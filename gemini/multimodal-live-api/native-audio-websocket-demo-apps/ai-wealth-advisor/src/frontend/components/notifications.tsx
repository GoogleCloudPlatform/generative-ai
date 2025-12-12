/*
// Copyright 2025 Google LLC
// 
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// 
//     https://www.apache.org/licenses/LICENSE-2.0
// 
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MessageCircle, Calendar, Upload, TrendingUp, AlertCircle, CheckCircle, Clock, X } from "lucide-react"

interface NotificationsPageProps {
  onStartAudioCall: (notificationText: string) => void
}

export function NotificationsPage({ onStartAudioCall }: NotificationsPageProps) {
  const notifications = [
    {
      id: 1,
      type: "alert",
      title: "Financial Advisor Notification: Based on your “Clients Like You” investment preference, I've identified an opportunity for equities and fixed income opportunities with the cash available in your account.",
      description: "Opportunity to invest cash in account",
      time: "4 hours ago",
      unread: true,
      icon: Calendar,
      color: "text-green-500",
    },
  ]

  const unreadCount = notifications.filter((n) => n.unread).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Notifications</h2>
          <p className="text-muted-foreground">Stay updated with your wealth management activities</p>
        </div>
        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <Badge variant="secondary" className="bg-primary/10 text-primary">
              {unreadCount} unread
            </Badge>
          )}
          <Button variant="outline" size="sm">
            Mark all as read
          </Button>
        </div>
      </div>

      {/* Notification Categories * /}
      <div className="flex gap-2 flex-wrap">
        <Button variant="default" size="sm">
          All
        </Button>
        <Button variant="ghost" size="sm">
          Messages
        </Button>
        <Button variant="ghost" size="sm">
          Meetings
        </Button>
        <Button variant="ghost" size="sm">
          Documents
        </Button>
        <Button variant="ghost" size="sm">
          Portfolio
        </Button>
        <Button variant="ghost" size="sm">
          Alerts
        </Button>
      </div>

      {/* Notifications List * /}
      <div className="space-y-3">
        {notifications.map((notification) => {
          const IconComponent = notification.icon
          return (
            <Card
              key={notification.id}
              className={`transition-colors hover:bg-accent/50 ${
                notification.unread ? "border-primary/20 bg-primary/5" : ""
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <div className={`p-2 rounded-full bg-muted/50 ${notification.color}`}>
                    <IconComponent className="h-4 w-4" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h3
                          className={`font-medium ${notification.unread ? "text-foreground" : "text-muted-foreground"}`}
                        >
                          {notification.title}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1">{notification.description}</p>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {notification.time}
                        </div>
                        {notification.unread && <div className="w-2 h-2 bg-primary rounded-full"></div>}
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>

                    {notification.type === "alert" && (
                      <div className="mt-3 flex gap-2">
                        <Button size="sm" variant="default" onClick={() => onStartAudioCall(notification.title)}>
                          Take Action
                        </Button>
                        <Button size="sm" variant="ghost">
                          Dismiss
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Load More * /}
      <div className="text-center">
        <Button variant="ghost" className="text-muted-foreground">
          Load more notifications
        </Button>
      </div>
    </div>
  )
}
*/
