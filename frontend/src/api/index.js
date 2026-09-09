import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建 axios 实例
const instance = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
instance.interceptors.request.use(
    config => {
        const token = localStorage.getItem('accessToken')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

// 是否正在刷新 Token
let isRefreshing = false

// 全局静默开关：页面自行做内联降级提示时，临时关闭全局错误弹窗
let globalSilent = false
export function setGlobalSilent(value) {
    globalSilent = value
}

// 响应拦截器
instance.interceptors.response.use(
    response => {
        return response.data
    },
    error => {
        const { response, config } = error

        // 调用方可传 skipErrorMessage 关闭全局错误弹窗，
        // 由页面自行做内联降级提示（如资料详情页的部分失败）
        const skipGlobalMessage = globalSilent || config?.skipErrorMessage === true

        if (response) {
            // 获取错误消息（优先使用后端返回的 message 或 detail）
            const errorMessage = response.data?.detail || response.data?.message || '请求失败'

            switch (response.status) {
                case 401:
                    // 如果是登录接口的 401，只显示一次错误提示
                    if (config.url?.includes('/auth/login')) {
                        if (!skipGlobalMessage) ElMessage.error(errorMessage)
                    } else {
                        // 非登录接口的 401，清除 token 并跳转登录页
                        localStorage.removeItem('accessToken')
                        localStorage.removeItem('refreshToken')
                        if (!isRefreshing) {
                            isRefreshing = true
                            if (!skipGlobalMessage) ElMessage.error('登录已过期，请重新登录')
                            router.push({ name: 'Login' })
                            setTimeout(() => { isRefreshing = false }, 2000)
                        }
                    }
                    break
                case 400:
                    if (!skipGlobalMessage) ElMessage.error(errorMessage)
                    break
                case 403:
                    if (!skipGlobalMessage) ElMessage.error('没有权限访问')
                    break
                case 404:
                    if (!skipGlobalMessage) ElMessage.error('请求的资源不存在')
                    break
                case 422:
                    // 验证错误，统一提取第一个错误信息显示
                    if (response.data?.detail && Array.isArray(response.data.detail)) {
                        const firstError = response.data.detail[0]
                        if (!skipGlobalMessage) ElMessage.error(firstError?.msg || '输入数据验证失败')
                    } else if (!skipGlobalMessage) {
                        ElMessage.error(errorMessage)
                    }
                    break
                case 500:
                    if (!skipGlobalMessage) ElMessage.error('服务器内部错误')
                    break
                default:
                    if (!skipGlobalMessage) ElMessage.error(errorMessage)
            }
        } else if (!skipGlobalMessage) {
            ElMessage.error('网络连接失败，请检查网络')
        }

        return Promise.reject(error)
    }
)

// API 接口定义
const api = {
    // 认证相关
    auth: {
        login: (data) => instance.post('/auth/login', data),
        register: (data) => instance.post('/auth/register', data),
        logout: () => instance.post('/auth/logout'),
        getCurrentUser: () => instance.get('/auth/me'),
        refreshToken: (refreshToken) => instance.post('/auth/refresh', { refresh_token: refreshToken })
    },

    // 用户管理
    users: {
        getList: (params) => instance.get('/users', { params }),
        getById: (id) => instance.get(`/users/${id}`),
        create: (data) => instance.post('/users', data),
        update: (id, data) => instance.put(`/users/${id}`, data),
        delete: (id) => instance.delete(`/users/${id}`),
        activate: (id) => instance.post(`/users/${id}/activate`),
        deactivate: (id) => instance.post(`/users/${id}/deactivate`),
        getStats: () => instance.get('/users/stats'),
        updateProfile: (data) => instance.put('/users/me', data),
        updatePassword: (data) => instance.put('/users/me/password', data)
    },

    // 资料服务（独立微服务，维护头像/部门/岗位，内部会调用用户服务合并数据）
    profiles: {
        // skipErrorMessage：页面用 Promise.allSettled 做合并降级，不弹全局错误
        getMerged: () => instance.get('/profiles/me', { skipErrorMessage: true }),
        update: (data) => instance.put('/profiles/me', data),
        setUpstreamFault: (failed) =>
            instance.put(`/profiles/demo/faults/upstream?failed=${failed}`, null, { skipErrorMessage: true }),
        setSelfFault: (failed) =>
            instance.put(`/profiles/demo/faults/self?failed=${failed}`, null, { skipErrorMessage: true }),
        resetFaults: () => instance.delete('/profiles/demo/faults', { skipErrorMessage: true })
    }
}

export default api
