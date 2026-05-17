import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardPage from '../pages/DashboardPage.vue'
import DataCenterPage from '../pages/DataCenterPage.vue'
import ReportWorkbenchPage from '../pages/ReportWorkbenchPage.vue'
import ReportHistoryPage from '../pages/ReportHistoryPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: DashboardPage, meta: { title: '今日总览' } },
    { path: '/data', component: DataCenterPage, meta: { title: '数据中心' } },
    { path: '/workbench', component: ReportWorkbenchPage, meta: { title: '日报工作台' } },
    { path: '/history', component: ReportHistoryPage, meta: { title: '历史日报' } },
    { path: '/settings', component: SettingsPage, meta: { title: '设置' } }
  ]
})

export default router
