import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('ca_token') || '',
    user: JSON.parse(localStorage.getItem('ca_user') || 'null')
  }),
  actions: {
    setLogin(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('ca_token', token)
      localStorage.setItem('ca_user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('ca_token')
      localStorage.removeItem('ca_user')
    }
  }
})
