/** Operations overview and dashboard configuration (`app/ops/dashboard`). */

import { del, get, post, put, type DeleteResult } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  Dashboard,
  DashboardCreateRequest,
  DashboardDetail,
  DashboardUpdateRequest,
  OverviewResponse,
  Widget,
  WidgetCreateRequest,
  WidgetUpdateRequest,
} from '@/types/ops'

/** `GET /ops/overview` */
export function fetchOverview(
  availabilityHours = 24,
  recentEventLimit = 10,
): Promise<OverviewResponse> {
  return get<OverviewResponse>(opsPath('/overview'), {
    params: { availability_hours: availabilityHours, recent_event_limit: recentEventLimit },
  })
}

/** `GET /ops/dashboards` */
export function listDashboards(
  page = 1,
  pageSize = 20,
  keyword?: string,
): Promise<Page<Dashboard>> {
  return get<Page<Dashboard>>(opsPath('/dashboards'), {
    params: { page, page_size: pageSize, keyword: keyword ?? undefined },
  })
}

/** `GET /ops/dashboards/{dashboard_id}` */
export function getDashboard(dashboardId: string): Promise<DashboardDetail> {
  return get<DashboardDetail>(opsPath(`/dashboards/${encodeURIComponent(dashboardId)}`))
}

/** `POST /ops/dashboards` — requires `OPS_DASHBOARD_MANAGE`. */
export function createDashboard(payload: DashboardCreateRequest): Promise<DashboardDetail> {
  return post<DashboardDetail>(opsPath('/dashboards'), payload)
}

/** `PUT /ops/dashboards/{dashboard_id}` — requires `OPS_DASHBOARD_MANAGE`. */
export function updateDashboard(
  dashboardId: string,
  payload: DashboardUpdateRequest,
): Promise<DashboardDetail> {
  return put<DashboardDetail>(opsPath(`/dashboards/${encodeURIComponent(dashboardId)}`), payload)
}

/** `DELETE /ops/dashboards/{dashboard_id}` — requires `OPS_DASHBOARD_MANAGE`. */
export function deleteDashboard(dashboardId: string): Promise<DeleteResult> {
  return del<DeleteResult>(opsPath(`/dashboards/${encodeURIComponent(dashboardId)}`))
}

/** `GET /ops/dashboards/{dashboard_id}/widgets` */
export function listWidgets(dashboardId: string): Promise<Widget[]> {
  return get<Widget[]>(opsPath(`/dashboards/${encodeURIComponent(dashboardId)}/widgets`))
}

/** `POST /ops/dashboards/{dashboard_id}/widgets` — requires `OPS_DASHBOARD_MANAGE`. */
export function createWidget(
  dashboardId: string,
  payload: WidgetCreateRequest,
): Promise<Widget> {
  return post<Widget>(opsPath(`/dashboards/${encodeURIComponent(dashboardId)}/widgets`), payload)
}

/** `PUT /ops/dashboards/{dashboard_id}/widgets/{widget_id}` — requires `OPS_DASHBOARD_MANAGE`. */
export function updateWidget(
  dashboardId: string,
  widgetId: string,
  payload: WidgetUpdateRequest,
): Promise<Widget> {
  return put<Widget>(
    opsPath(`/dashboards/${encodeURIComponent(dashboardId)}/widgets/${encodeURIComponent(widgetId)}`),
    payload,
  )
}

/** `DELETE /ops/dashboards/{dashboard_id}/widgets/{widget_id}` — requires `OPS_DASHBOARD_MANAGE`. */
export function deleteWidget(dashboardId: string, widgetId: string): Promise<DeleteResult> {
  return del<DeleteResult>(
    opsPath(`/dashboards/${encodeURIComponent(dashboardId)}/widgets/${encodeURIComponent(widgetId)}`),
  )
}
