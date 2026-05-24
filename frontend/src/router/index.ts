import { createRouter, createWebHashHistory } from 'vue-router'

import DataCenter from '../pages/DataCenter.vue'
import ReportWorkbench from '../pages/ReportWorkbench.vue'
import Settings from '../pages/Settings.vue'
import TodayOverview from '../pages/TodayOverview.vue'

/**
 * 前端路由骨架。
 *
 * MVP 只保留四个正式页面：
 * - 今日总览
 * - 数据中心
 * - 日报工作台
 * - 设置
 *
 * 旧路径只做 redirect，避免历史链接失效。
 */

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/today' },
    { path: '/today', component: TodayOverview, meta: { title: '今日总览' } },
    { path: '/dashboard', redirect: '/today' },
    { path: '/data', component: DataCenter, meta: { title: '数据中心' } },
    { path: '/report', component: ReportWorkbench, meta: { title: '日报工作台' } },
    { path: '/workbench', redirect: '/report' },
    { path: '/history', redirect: '/report' },
    { path: '/settings', component: Settings, meta: { title: '设置' } }
  ]
})

export default router
