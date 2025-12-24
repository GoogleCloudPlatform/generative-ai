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

"use client";

import { useState } from "react";
import Image from "next/image";
// import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ChevronRight, X, HelpCircle } from "lucide-react";
import ProfileIcon from "./ProfileIcon";
import "./ProfileMenu.css";

export function ProfileMenu() {
  const [isOpen, setIsOpen] = useState(false);
  //   const router = useRouter();

  //   const handleNotificationClick = () => {
  //     setIsOpen(false);
  //     const notificationText = "You have a CD maturing, log in for more information.";
  //     router.push(`/audio-call?start_conversation=true&notification_text=${encodeURIComponent(notificationText)}`);
  //   };

  return (
    <>
      {!isOpen && (
        <Button
          variant="outline"
          className="profile-menu-button"
          onClick={() => setIsOpen(true)}
        >
          <ProfileIcon className="!h-7 !w-7" />
        </Button>
      )}
      {isOpen && (
        <div className="absolute top-0 right-0 h-full w-full z-10">
          <div className="my-wealth-drawer absolute top-0 right-0 h-full">
            <div className="flex justify-between items-center mb-8">
              <div className="flex items-center">
                <ChevronRight className="transform -rotate-180" />
                <ProfileIcon className="h-6 w-6 mx-2" />
                <h2 className="text-xl font-light">Wealth Profile</h2>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
                <X className="h-7 w-7" />
              </Button>
            </div>

            <div className="relationship-config-section">
              <p className="section-title">Digital Advisor</p>
              {/* <p className="section-description">
                Personalize your interactions with your Wealth digital advisor.
              </p> */}
              <div className="avatars-container">
                <div className="avatar active">
                  <Image src="figma/customize-avatar-profile-drawer.png" alt="Ava" />
                  {/* <span>Ava</span> */}
                </div>
                {/* <div className="avatar active">
                  <Image src="/figma/ava.png" alt="Ava" width={48} height={48} />
                  <span>Ava</span>
                </div>
                <div className="avatar">
                  <Image
                    src="/figma/james.png"
                    alt="James"
                    width={48}
                    height={48}
                  />
                  <span>James</span>
                </div>
                <div className="avatar">
                  <Image src="/figma/jade.png" alt="Jade" width={48} height={48} />
                  <span>Jade</span>
                </div>
                <div className="avatar">
                  <Image src="/figma/amit.png" alt="Amit" width={48} height={48} />
                  <span>Amit</span>
                </div> */}
              </div>
            </div>

            {/* <div className="sound-interaction-section">
              <p className="sound-interaction-description">
                Hi, I'm Ava and here's how our interactions would sound like...
              </p>
              <div className="sound-player">
                <Play className="play-button" />
                <div className="sound-wave">{soundWaveBars}</div>
              </div>
            </div> */}

            <div className="profile-section">
              <p className="section-title">WEALTH PROFILE</p>
              <div className="profile-card">
                <Image
                  src="/figma/andy.png"
                  alt="Kevin Smith"
                  width={64}
                  height={64}
                />
                <div className="profile-info">
                  <h3>Kevin Smith</h3>
                  <p>View profile & connections</p>
                </div>
              </div>

              {/* <div className="info-card notification-card" onClick={handleNotificationClick}>
                <div className="info-card-header">
                  <p className="info-card-title">NOTIFICATIONS</p>
                  <HelpCircle />
                </div>
                <p className="info-card-content">You have a CD maturing, log in for more information.</p>
                <div className="info-card-button">
                  Talk with Ava
                </div>
              </div> */}

              <div className="info-card">
                <div className="info-card-header">
                  <p className="info-card-title">PERFORMANCE & GROWTH</p>
                  <HelpCircle />
                </div>
                <p className="info-card-content">More information needed</p>
                <div className="info-card-button">
                  Tell Ava About Portfolio
                </div>
              </div>

              <div className="info-card">
                <div className="info-card-header">
                  <p className="info-card-title">RISK & STABILITY</p>
                  <HelpCircle />
                </div>
                <p className="info-card-content">More information needed</p>
              </div>

              <div className="info-card">
                <div className="info-card-header">
                  <p className="info-card-title">Personalisation</p>
                </div>
                <p className="info-card-content">Get informed on latest wealth and financial trends</p>
                <div className="info-card-button">
                  Talk with Ava
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
