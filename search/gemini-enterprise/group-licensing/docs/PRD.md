## **1. Executive Summary** {#1.-executive-summary}

Gemini Enterprise licensing operates on a per-user model that currently lacks the granularity required for large-scale enterprise deployment. The native "Auto-assign license" feature in the Google Cloud Console for Gemini Enterprise is binary (on/off) and cannot distinguish between license SKUs (e.g., Standard, Enterprise, Enterprise Plus, vs. Frontline) nor does it respect user group membership.

This document outlines the requirements for an automated solution to manage license lifecycles. This solution will bridge the gap between Billing Account subscriptions and Project-level enforcement, utilizing a **Scheduled Batch Reconciliation** approach for robust state management, eventual consistency, and cleanup.

## **2. Problem Statement** {#2.-problem-statement}

Enterprise customers managing Gemini Enterprise licenses face significant friction due to these primary limitations in the current Cloud Console experience:

1. **No SKU Differentiation:** The "Auto-assign" toggle grants a license to any user accessing the project, regardless of whether they require a "Standard" or "Frontline" seat. This leads to license waste and compliance issues.

2. **Lack of Group Inheritance:** Admins cannot map Google Cloud Identity or external IdP groups (e.g., "Sales_NorthAM") to specific license types.

3. **Missing Automated Removal & Cleanup Tools:** There is no automation to assist Admins with automatic removal nor automatic re-assignment of Gemini Enterprise licenses. This is causing maintainability friction for admins & contention during renewals.

4. **No Bulk Management:** The Google Cloud Console manage user license assignment page currently does not afford Admins the ability to assign licenses in bulk using a CSV or other structured file. The only option available to Admins is to manually enter multiple email addresses on the UI text box directly.

5. **Manual Toil:** The only viable workaround currently is manual assignment per user, which is operationally unscalable for organizations with thousands of seats.

## **3. Goals & Non-Goals** {#3.-goals-&-non-goals}

### **3.1 Goals** {#3.1-goals}

* **Group-Based Assignment:** Enable administrators to map specific Identity Groups (Google Groups) to specific Gemini Enterprise license SKUs.

* **Scheduled Reconciliation (Batch Job):** Implement a periodic "state-of-the-world" sweep that serves two critical functions:

  * **Garbage Collection (Leaver Support):** Identify and revoke licenses for users who are inactive or no longer present in valid groups.

  * **Self-Healing (Joiner Support):** Identify valid group members missing a license (e.g., due to accidental manual deletion or API failures) and re-provision them, ensuring eventual consistency.

### **3.2 Non-Goals** {#3.2-non-goals}

* **Real-Time Lifecycle Management:** Immediate "Joiner/Leaver" support via push notifications is strictly **out of scope** due to API limitations and security concerns.

* **3rd Party Identity / Workforce Identity Federation (WIF):** Support for ephemeral identities authenticated via WIF is strictly **out of scope** due to technical feasibility concerns.

* **Billing Account Level Enforcement:** This solution focuses on Project-level assignment automation, not changing the underlying billing infrastructure.

## **4. User Stories** {#4.-user-stories}

* **Use Case 1 (SKU Segmentation):** As a System Administrator, I want to ensure that my "Field Sales" group automatically receives "Frontline" licenses and my "Software Engineering" group receives "Enterprise" licenses, so that I optimize my spend.

* **Use Case 2 (Onboarding):** As a Hiring Manager, I want new employees added to the "Gemini-Users" group to automatically have a license assigned without filing a ticket.

* **Use Case 3 (Scheduled Offboarding):** As a Security Admin, I want a user's Gemini license to be revoked during the next scheduled reconciliation job when they are removed from the "Active Employees" group to maintain compliance.

* **Use Case 4 (Hygiene & Reliability):** As a FinOps Lead, I want a nightly job that sweeps my user base to remove unused licenses (saving money) while simultaneously fixing any missing assignments for active users (reducing support tickets).

## **5. Functional Requirements** {#5.-functional-requirements}

### **5.1 Configuration & Mapping** {#5.1-configuration-&-mapping}

* **FR-01:** The system MUST allow admins to define a configuration file (or map) linking one or more Google Groups identified by group email address(es) to a specific Gemini License SKU ID.

* **FR-02:** The system MUST support multiple distinct mappings within the same GCP Project. This also needs to be scalable across multiple GCP Projects.

### **5.2 Batch Reconciliation Engine** {#5.2-batch-reconciliation-engine}

* **FR-03 (The Sweeper):** The system MUST support a configurable schedule (e.g., daily/weekly) to scan the full membership of all configured Google Groups against the list of currently assigned licenses.

* **FR-04 (Garbage Collection Logic):**

  * If a user HAS a license but HAS NOT logged in for `X` days (Staleness): **Revoke License.** Staleness checking is optional and disabled when `staleness_threshold_days` is `0` or omitted from configuration.
  * If a user has **never** logged in, the staleness reference date falls back to the license assignment date. This prevents a recently provisioned account from being immediately revoked before the user has had a chance to sign in. If the user still has not logged in after `X` days from assignment, the license is revoked.

* **FR-05 (Self-Healing Logic):**

  * If a user IS in a valid group but DOES NOT HAVE a license: **Grant License.**

* **FR-06 (Conflict Resolution):** If a user is in multiple groups mapped to different SKUs, the batch job MUST deterministically apply a precedence rule (e.g., "Enterprise" trumps "Frontline").

## **6. Technical Constraints** {#6.-technical-constraints}

* **API Rate Limits:** The solution must respect the quotas for the `Cloud Billing` and `Enterprise License Manager` APIs, implementing exponential backoff where necessary.

* **Latency:** License assignment and revocation are eventually consistent and occur based on the execution frequency of the scheduled batch jobs.

* **License Type:** Customer should be on Gemini Enterprise subscription licensing SKUs (not on the legacy Agentspace licensing mechanism).

## **7. Metrics & Success Criteria** {#7.-metrics-&-success-criteria}

* **Reduction in Unassigned Seats:** % utilization of purchased licenses increases.

* **Operational Savings:** Reduction in manual "Grant License" tickets filed.

* **Security Compliance:** Time-to-revocation for terminated employees \< 24 hours (or the configured batch frequency).

* **Accuracy:** \< 1% of active users reporting "License Not Found" errors (indicating aggressive Garbage Collection).
