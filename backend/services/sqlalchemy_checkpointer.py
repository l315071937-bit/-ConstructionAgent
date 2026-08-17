"""Durable LangGraph checkpoints stored in the application's SQL database."""
import json
import threading
from collections.abc import Iterator, Sequence
from functools import wraps
from typing import Any

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

from db.models import (LangGraphCheckpoint, LangGraphCheckpointBlob,
                       LangGraphCheckpointWrite)
from db.session import SessionLocal


def _version_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _locked(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


class SQLAlchemyCheckpointSaver(BaseCheckpointSaver):
    """Small SQLAlchemy saver compatible with SQLite tests and PostgreSQL runtime."""

    def __init__(self, session_factory=SessionLocal, **kwargs):
        super().__init__(**kwargs)
        self.session_factory = session_factory
        self._lock = threading.RLock()

    @staticmethod
    def _config(thread_id: str, namespace: str,
                checkpoint_id: str) -> dict:
        return {"configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": namespace,
            "checkpoint_id": checkpoint_id,
        }}

    def _tuple(self, db, row: LangGraphCheckpoint) -> CheckpointTuple:
        checkpoint = self.serde.loads_typed(
            (row.checkpoint_type, row.checkpoint_data))
        channel_values = {}
        for channel, version in checkpoint.get("channel_versions", {}).items():
            blob = (db.query(LangGraphCheckpointBlob)
                    .filter_by(thread_id=row.thread_id,
                               checkpoint_ns=row.checkpoint_ns,
                               channel=channel,
                               version=_version_key(version)).first())
            if blob and blob.value_type != "empty":
                channel_values[channel] = self.serde.loads_typed(
                    (blob.value_type, blob.value_data))
        writes = (db.query(LangGraphCheckpointWrite)
                  .filter_by(thread_id=row.thread_id,
                             checkpoint_ns=row.checkpoint_ns,
                             checkpoint_id=row.checkpoint_id)
                  .order_by(LangGraphCheckpointWrite.task_id,
                            LangGraphCheckpointWrite.write_index).all())
        config = self._config(row.thread_id, row.checkpoint_ns,
                              row.checkpoint_id)
        return CheckpointTuple(
            config=config,
            checkpoint={**checkpoint, "channel_values": channel_values},
            metadata=self.serde.loads_typed(
                (row.metadata_type, row.metadata_data)),
            parent_config=(self._config(
                row.thread_id, row.checkpoint_ns, row.parent_checkpoint_id)
                if row.parent_checkpoint_id else None),
            pending_writes=[
                (item.task_id, item.channel,
                 self.serde.loads_typed((item.value_type, item.value_data)))
                for item in writes
            ],
        )

    @_locked
    def get_tuple(self, config: dict) -> CheckpointTuple | None:
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        namespace = configurable.get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        db = self.session_factory()
        try:
            query = db.query(LangGraphCheckpoint).filter_by(
                thread_id=thread_id, checkpoint_ns=namespace)
            if checkpoint_id:
                row = query.filter_by(checkpoint_id=checkpoint_id).first()
            else:
                row = query.order_by(
                    LangGraphCheckpoint.checkpoint_id.desc()).first()
            return self._tuple(db, row) if row else None
        finally:
            db.close()

    def list(self, config: dict | None, *, filter: dict | None = None,
             before: dict | None = None,
             limit: int | None = None) -> Iterator[CheckpointTuple]:
        db = self.session_factory()
        try:
            query = db.query(LangGraphCheckpoint)
            if config:
                configurable = config["configurable"]
                query = query.filter_by(thread_id=configurable["thread_id"])
                if "checkpoint_ns" in configurable:
                    query = query.filter_by(
                        checkpoint_ns=configurable["checkpoint_ns"])
                if checkpoint_id := get_checkpoint_id(config):
                    query = query.filter_by(checkpoint_id=checkpoint_id)
            if before and (before_id := get_checkpoint_id(before)):
                query = query.filter(
                    LangGraphCheckpoint.checkpoint_id < before_id)
            query = query.order_by(LangGraphCheckpoint.checkpoint_id.desc())
            if limit is not None:
                query = query.limit(limit)
            for row in query.all():
                item = self._tuple(db, row)
                if filter and not all(
                        item.metadata.get(key) == value
                        for key, value in filter.items()):
                    continue
                yield item
        finally:
            db.close()

    @_locked
    def put(self, config: dict, checkpoint: dict, metadata: dict,
            new_versions: dict) -> dict:
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        namespace = configurable.get("checkpoint_ns", "")
        checkpoint_copy = checkpoint.copy()
        values = checkpoint_copy.pop("channel_values", {})
        checkpoint_type, checkpoint_data = self.serde.dumps_typed(
            checkpoint_copy)
        metadata_type, metadata_data = self.serde.dumps_typed(
            get_checkpoint_metadata(config, metadata))
        db = self.session_factory()
        try:
            db.merge(LangGraphCheckpoint(
                thread_id=thread_id, checkpoint_ns=namespace,
                checkpoint_id=checkpoint["id"],
                parent_checkpoint_id=configurable.get("checkpoint_id"),
                checkpoint_type=checkpoint_type,
                checkpoint_data=checkpoint_data,
                metadata_type=metadata_type, metadata_data=metadata_data))
            for channel, version in new_versions.items():
                if channel in values:
                    value_type, value_data = self.serde.dumps_typed(
                        values[channel])
                else:
                    value_type, value_data = "empty", b""
                db.merge(LangGraphCheckpointBlob(
                    thread_id=thread_id, checkpoint_ns=namespace,
                    channel=channel, version=_version_key(version),
                    value_type=value_type, value_data=value_data))
            db.commit()
        finally:
            db.close()
        return self._config(thread_id, namespace, checkpoint["id"])

    @_locked
    def put_writes(self, config: dict,
                   writes: Sequence[tuple[str, Any]], task_id: str,
                   task_path: str = "") -> None:
        configurable = config["configurable"]
        db = self.session_factory()
        try:
            for index, (channel, value) in enumerate(writes):
                write_index = WRITES_IDX_MAP.get(channel, index)
                identity = {
                    "thread_id": configurable["thread_id"],
                    "checkpoint_ns": configurable.get("checkpoint_ns", ""),
                    "checkpoint_id": configurable["checkpoint_id"],
                    "task_id": task_id, "write_index": write_index,
                }
                if write_index >= 0 and db.query(
                        LangGraphCheckpointWrite).filter_by(**identity).first():
                    continue
                value_type, value_data = self.serde.dumps_typed(value)
                db.merge(LangGraphCheckpointWrite(
                    **identity, channel=channel, value_type=value_type,
                    value_data=value_data, task_path=task_path))
            db.commit()
        finally:
            db.close()

    @_locked
    def delete_thread(self, thread_id: str) -> None:
        db = self.session_factory()
        try:
            for model in (LangGraphCheckpointWrite,
                          LangGraphCheckpointBlob, LangGraphCheckpoint):
                db.query(model).filter_by(thread_id=thread_id).delete(
                    synchronize_session=False)
            db.commit()
        finally:
            db.close()
