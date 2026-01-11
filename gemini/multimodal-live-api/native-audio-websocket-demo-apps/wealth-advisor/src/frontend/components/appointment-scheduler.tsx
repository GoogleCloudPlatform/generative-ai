// Copyright 2026 Google LLC
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

import React, { useState, useEffect } from "react"
import "./appointment-scheduler.css"

export interface AppointmentSchedulerData {
  type: "appointment_scheduler"
  title: string
  advisor: {
    name: string
    title: string
    image: string
  }
  time_slots: {
    date: string
    slots: string[]
  }[]
}

interface AppointmentSchedulerProps {
  data: AppointmentSchedulerData
  onClose: () => void
}

export const AppointmentScheduler: React.FC<AppointmentSchedulerProps> = ({
  data,
  onClose,
}) => {
  const [selectedDate, setSelectedDate] = useState<string | null>(
    data.time_slots[0]?.date || null,
  )
  const [selectedTime, setSelectedTime] = useState<string | null>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true)
    }, 7000) // Reduced delay for faster appearance
    return () => clearTimeout(timer)
  }, [])

  const handleDateClick = (date: string) => {
    setSelectedDate(date)
    setSelectedTime(null) // Reset time when date changes
  }

  const handleTimeClick = (time: string) => {
    setSelectedTime(time)
  }

  const handleConfirm = async () => {
    if (selectedDate && selectedTime) {
      onClose()
    }
  }

  const getDayOfWeek = (dateString: string) => {
    const day = dateString.split(",")[0]
    return day.substring(0, 3).toUpperCase()
  }

  const getDayOfMonth = (dateString: string) => {
    const parts = dateString.split(", ")
    return parts[1]
  }

  if (!isVisible) {
    return null
  }


  return (
    <div className="scheduler-overlay">
      <div className="scheduler-card sweep-in">
        <div className="scheduler-header">
          <h2 className="scheduler-title">Schedule Meeting</h2>
          <button onClick={onClose} className="close-icon">
            <svg width="19" height="19" viewBox="0 0 19 19" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0.5 17.5C0.5 18.0523 0.947716 18.5 1.5 18.5L10.5 18.5C11.0523 18.5 11.5 18.0523 
                11.5 17.5C11.5 16.9477 11.0523 16.5 10.5 16.5L2.5 16.5L2.5 8.5C2.5 7.94771 2.05229 7.5 1.5 
                7.5C0.947716 7.5 0.5 7.94771 0.5 8.5V17.5ZM18 1L17.2929 0.292892L0.792892 16.7929L1.5 17.5L2.20711 
                18.2071L18.7071 1.70711L18 1Z" fill="white"/>
            </svg>
          </button>
        </div>

        <div className="scheduler-body">
          <div className="timezone-section">
            <p className="timezone-text">
              YOUR CURRENT TIME ZONE - EASTERN TIME (ET)
            </p>
            <button className="change-timezone-btn">Change time zone</button>
          </div>

          <div className="divider" />

          <div className="date-selection-section">
            <p className="select-label">SELECT A DATE</p>
            <div className="date-options">
              {data.time_slots.map((day) => (
                <button
                  key={day.date}
                  className={`date-option ${selectedDate === day.date ? "selected" : ""}`}
                  onClick={() => handleDateClick(day.date)}
                >
                  <span className="day-of-week">{getDayOfWeek(day.date)}</span>
                  <span className="day-of-month">
                    {getDayOfMonth(day.date)}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="divider" />

          <div className="time-selection-section">
            <p className="select-label">SELECT A TIME</p>
            <div className="time-options">
              {data.time_slots
                .find((day) => day.date === selectedDate)
                ?.slots.map((slot) => (
                  <button
                    key={slot}
                    className={`time-option ${selectedTime === slot ? "selected" : ""}`}
                    onClick={() => handleTimeClick(slot)}
                  >
                    {slot}
                  </button>
                ))}
            </div>
          </div>
        </div>

        <div className="scheduler-footer">
          <button
            className="schedule-btn"
            onClick={handleConfirm}
            disabled={!selectedDate || !selectedTime}
          >
            Schedule
          </button>
          <button className="back-btn" onClick={onClose}>
            Back
          </button>
        </div>
      </div>
    </div>
  )
}
