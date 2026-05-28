import { createRouter, createWebHashHistory } from 'vue-router'

const AppProfiles = () => import('../pages/AppProfiles.vue')
const DataCenter = () => import('../pages/DataCenter.vue')
const ReportWorkbench = () => import('../pages/ReportWorkbench.vue')
const Settings = () => import('../pages/Settings.vue')
const TodayOverview = () => import('../pages/TodayOverview.vue')

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'today',
      component: TodayOverview,
      meta: {
        title: '今日总览'
      }
    },
    {
      path: '/data',
      name: 'data-center',
      component: DataCenter,
      meta: {
        title: '数据中心'
      }
    },
    {
      path: '/apps',
      name: 'app-profiles',
      component: AppProfiles,
      meta: {
        title: '应用配置'
      }
    },
    {
      path: '/reports',
      name: 'report-workbench',
      component: ReportWorkbench,
      meta: {
        title: '日报工作台'
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings,
      meta: {
        title: '设置'
      }
    },
    {
      path: '/dashboard',
      redirect: '/'
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

export default router
