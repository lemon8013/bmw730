/**
 * Notification attempts and channels (`app/ops/notifications`).
 *
 * Channel `config` is echoed back by the backend but never contains a
 * credential, so it is safe to render as JSON.
 */

import { get, post, put } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  AlertNotification,
  NotificationChannel,
  NotificationChannelCreateRequest,
  NotificationChannelUpdateRequest,
} from '@/types/ops'

/** `GET /ops/notifications` */
export function listNotifications(
  page = 1,
  pageSize = 20,
  status?: string,
  alertId?: string,
): Promise<Page<AlertNotification>> {
  return get<Page<AlertNotification>>(opsPath('/notifications'), {
    params: {
      page,
      page_size: pageSize,
      status: status ?? undefined,
      alert_id: alertId ?? undefined,
    },
  })
}

/** Filters accepted by `GET /ops/notification-channels`. */
export interface ChannelFilters {
  keyword?: string
  channelType?: string
  enabled?: boolean
}

/** `GET /ops/notification-channels` */
export function listNotificationChannels(
  page = 1,
  pageSize = 20,
  filters: ChannelFilters = {},
): Promise<Page<NotificationChannel>> {
  return get<Page<NotificationChannel>>(opsPath('/notification-channels'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      channel_type: filters.channelType ?? undefined,
      enabled: filters.enabled ?? undefined,
    },
  })
}

/** `POST /ops/notification-channels` — requires `OPS_ALERT_MANAGE`. */
export function createNotificationChannel(
  payload: NotificationChannelCreateRequest,
): Promise<NotificationChannel> {
  return post<NotificationChannel>(opsPath('/notification-channels'), payload)
}

/** `PUT /ops/notification-channels/{channel_id}` — requires `OPS_ALERT_MANAGE`. */
export function updateNotificationChannel(
  channelId: string,
  payload: NotificationChannelUpdateRequest,
): Promise<NotificationChannel> {
  return put<NotificationChannel>(
    opsPath(`/notification-channels/${encodeURIComponent(channelId)}`),
    payload,
  )
}
