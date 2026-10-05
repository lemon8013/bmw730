/** Notification administration (`app/admin/notifications`). */

import { get, post } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  CreateNotificationRequest,
  Notification,
  NotificationPage,
  NotificationQuery,
  NotificationTypeStat,
} from '@/types/ops'

/** `GET /admin/notifications` */
export function listNotifications(query: NotificationQuery = {}): Promise<Page<Notification>> {
  return get<Page<Notification>>('/admin/notifications', { params: query })
}

/** `POST /admin/notifications` */
export function sendNotification(payload: CreateNotificationRequest): Promise<Notification> {
  return post<Notification>('/admin/notifications', payload, {
    vctn: {
      idempotencyKey: `send-notification:${payload.user_type}:${payload.user_id}:${payload.title}`,
    },
  })
}

/** `GET /admin/notifications/stats` */
export function getNotificationStats(
  start?: string,
  end?: string,
): Promise<NotificationTypeStat[]> {
  return get<NotificationTypeStat[]>('/admin/notifications/stats', {
    params: { start, end },
  })
}

/** `POST /admin/notifications/{notification_id}/read` */
export function markNotificationRead(notificationId: string): Promise<Notification> {
  return post<Notification>(`/admin/notifications/${notificationId}/read`)
}

/** `GET /notifications` — the signed-in identity's own inbox. */
export function listMyNotifications(
  unreadOnly = false,
  page = 1,
  pageSize = 20,
): Promise<NotificationPage> {
  return get<NotificationPage>('/notifications', {
    params: { unread_only: unreadOnly, page, page_size: pageSize },
  })
}

/** `POST /notifications/{notification_id}/read` */
export function markMyNotificationRead(notificationId: string): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>(`/notifications/${notificationId}/read`)
}

/** `POST /notifications/read-all` */
export function markAllMyNotificationsRead(): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>('/notifications/read-all')
}
