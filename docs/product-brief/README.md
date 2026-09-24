# Tuviora – Project Brief

## Project Name

**Tuviora**

## Category

Event Management, Payments and Communication Platform

## Proposed Technology

* **Backend:** Django / Django REST Framework
* **Frontend:** React
* **Communication:** Africa's Talking APIs
* **Payments:** Mobile Money and card payment integration
* **Database:** PostgreSQL

---

## 1. Project Overview

**Tuviora** is a digital event management and communication platform designed to help event organizers manage the complete event journey from a single place.

The platform allows organizers to create events, register attendees, collect event payments, communicate important updates, coordinate event teams and manage attendee check-in.

Tuviora also integrates communication services such as **SMS and USSD**, allowing organizers to reach attendees who may have limited internet access or may not consistently use smartphones.

The aim is to reduce the number of separate tools organizers currently need to manage an event.

---

## 2. The Problem

Event organizers often rely on several disconnected tools when planning and managing events.

For example, an organizer may use:

* Google Forms for registrations
* Excel or Google Sheets for attendee records
* WhatsApp groups for communication
* Mobile Money numbers for payments
* Phone calls for team coordination
* Printed or manually maintained lists for event check-in

This creates fragmented workflows and makes it difficult to maintain an accurate view of registrations, payments, communication and attendance.

Organizers may also struggle to reach attendees when internet connectivity is unreliable or when participants do not have access to smartphones.

For paid events, manually verifying payments can create an additional administrative burden and increase the risk of errors.

---

## 3. The Solution

Tuviora brings the essential parts of event management into one platform.

Organizers can:

* Create and publish events
* Accept attendee registrations
* Collect event payments
* Track paid and unpaid registrations
* Manage attendee records
* Send SMS notifications and reminders
* Provide important event information through USSD
* Assign team members different responsibilities
* Manage attendee check-in
* Monitor registrations, payments and attendance from a central dashboard

Attendees can register for events, make payments, receive confirmations and access important event information without relying entirely on internet-based communication.

---

## 4. Core Value Proposition

**Tuviora helps event organizers register, collect payments from, communicate with and manage attendees from one platform, while supporting both internet and mobile communication channels.**

The platform is particularly useful for events where organizers need to communicate reliably with large groups of attendees.

---

## 5. Core User Journey

A typical event on Tuviora would follow the journey below:

**Organizer creates event**

↓

**Organizer configures ticket type, price, venue and registration information**

↓

**Tuviora generates an event registration link and QR code**

↓

**Attendee opens the event page and registers**

↓

**If the event is paid, the attendee completes payment**

↓

**Payment is verified automatically**

↓

**Attendee receives confirmation through SMS and/or email**

↓

**Organizer sends reminders and event updates**

↓

**Attendee arrives at the venue**

↓

**Event team scans attendee QR code or confirms registration**

↓

**Attendee is marked as checked in**

↓

**Organizer views final registration, payment and attendance information**

---

## 6. Event Types

Tuviora should support two main categories of events.

### Free Events

Attendees register without making a payment.

Once registration is completed, the attendee receives confirmation and event information.

### Paid Events

The organizer specifies the ticket price and available ticket categories.

The attendee registers and completes payment before receiving a confirmed ticket.

Possible ticket categories could include:

* Early Bird
* Standard
* VIP
* Student
* Group Ticket

Advanced ticket structures can be introduced after the initial MVP.

---

## 7. Payments

Payments should form part of the event registration process for paid events.

Tuviora should integrate with an appropriate payment provider that can support payment methods such as:

* Mobile Money
* Debit or credit cards
* Other locally supported payment methods

Tuviora should not operate as a financial institution or hold customer funds unnecessarily.

Instead, the payment provider should process the transaction while Tuviora records information such as:

* Transaction reference
* Event
* Attendee
* Amount
* Payment method
* Payment status
* Payment date

Possible payment statuses include:

* Pending
* Successful
* Failed
* Refunded

Once payment is confirmed, the attendee's registration should automatically change to **Paid/Confirmed**.

Tuviora's chosen payment provider is **MarzPay** (https://wallet.wearemarz.com), covering Mobile Money and card collections. See [Payments](../payments/README.md) for the integration design and current implementation status.

---

## 8. Organizer Dashboard

Each organizer should have access to a dashboard showing the status of their events.

Example information could include:

* Total registrations
* Confirmed attendees
* Paid registrations
* Pending payments
* Total ticket revenue
* Checked-in attendees
* Upcoming events
* Recent registrations

For example:

**500 Registered | 420 Paid | 35 Pending | 45 Complimentary | 386 Checked In**

This gives organizers a clear operational view of their event.

---

## 9. Attendee Registration

Each event should have a dedicated registration page.

The organizer should be able to determine what information is collected.

Typical information may include:

* Full name
* Phone number
* Email address
* Organization
* Ticket type
* Additional event-specific information

After successful registration, Tuviora should generate a unique registration reference for the attendee.

Where appropriate, a QR code can also be generated for event check-in.

---

## 10. Event Communication

Communication is one of the main differentiators of Tuviora.

Organizers should be able to send messages directly to registered attendees.

Examples include:

* Registration confirmations
* Payment confirmations
* Event reminders
* Venue changes
* Schedule updates
* Important announcements
* Thank-you messages after the event

Messages can initially be delivered through **SMS**, with additional channels introduced later.

---

## 11. USSD Event Access

Tuviora should provide basic event information through USSD for attendees who may not have reliable internet access.

An example flow could be:

**Welcome to Tuviora**

1. Find My Event
2. Event Details
3. Confirm Attendance
4. Check Registration

The attendee could enter an event or registration code and receive essential information such as:

* Event name
* Date
* Time
* Venue
* Registration status

USSD should complement the web platform rather than attempt to reproduce every web feature.

---

## 12. Event Team Management

Event owners should be able to invite team members to help manage an event.

Role-based permissions should ensure that team members only access the functions relevant to their responsibilities.

Possible roles include:

### Event Owner

Has complete control over the event.

### Event Manager

Can manage event information, attendees and operations.

### Registration Officer

Can view registrations and manage event-day check-in.

### Communications Officer

Can prepare and send attendee communications.

Additional roles can be introduced as the platform grows.

---

## 13. Event Check-In

Tuviora should allow event teams to confirm when registered attendees arrive at the venue.

Check-in could be performed using:

* QR code scanning
* Registration reference
* Phone number search
* Manual attendee lookup

Once checked in, the attendee's status should be updated.

Possible registration states could therefore include:

**Registered → Payment Pending → Confirmed → Checked In**

For free events, the payment step would be skipped.

---

## 14. MVP Features

The first version of Tuviora should focus on the core event management workflow.

### Organizer Features

* Organizer account registration and login
* Create, edit and manage events
* Configure free or paid events
* Configure ticket prices
* Generate event registration link
* Generate event QR code
* View attendee registrations
* Track payment status
* View event dashboard
* Invite event team members
* Assign team roles
* Send SMS notifications
* Manage attendee check-in

### Attendee Features

* View event information
* Register for an event
* Select ticket type
* Make payment for paid events
* Receive SMS confirmation
* Receive registration reference/QR code
* Access selected event information through USSD
* Check registration status

---

## 15. Features Outside the Initial MVP

The following features can be considered after the core platform has been validated:

* Public event marketplace and discovery
* Voice conference calling
* Advanced event analytics
* Event seating plans
* Discount and promotional codes
* Waitlists
* Automated refunds
* Event certificates
* Recurring events
* Event sponsorship management
* Vendor management
* Event budgeting
* Attendee networking
* WhatsApp integration
* AI-powered event assistants
* Event recommendations

Keeping these outside the MVP will allow the initial product to focus on solving the primary event management problem effectively.

---

## 16. Target Users

Tuviora can serve several categories of users, including:

* Professional event organizers
* Conference organizers
* Workshop and training coordinators
* Universities and educational institutions
* Community organizations
* Churches and religious organizations
* NGOs
* Corporate organizations
* Business associations
* Wedding and social-event organizers
* Event attendees

The initial product should preferably focus on a smaller number of event categories before expanding into every type of event.

---

## 17. Example Use Case

A conference organizer expects **500 attendees**.

Instead of using separate tools for registration, payment tracking, attendee communication and check-in, the organizer creates the event on Tuviora.

Tuviora generates a registration page and QR code.

Attendees register and pay their conference fee.

Successful payments are automatically linked to registrations.

Attendees receive confirmation by SMS.

Before the conference, the organizer sends reminders to all confirmed attendees.

An attendee without reliable internet access can retrieve basic event details through USSD.

On the event day, staff scan attendee QR codes at the entrance.

The organizer's dashboard then provides a real-time view of:

* Registrations
* Payments
* Outstanding payments
* Confirmed attendees
* Checked-in attendees

This replaces several disconnected processes with one coordinated workflow.

---

## 18. Revenue Model

Tuviora could eventually generate revenue through a combination of:

### Platform Fees

Organizers could pay a small platform fee for paid events.

### Subscription Plans

Regular event organizers could subscribe to plans providing additional events, users or features.

### Communication Charges

SMS or other communication costs could be passed through to organizers with a small service margin.

### Premium Event Features

Advanced functionality could be available as paid add-ons.

The exact pricing model should be validated with potential organizers before being finalized.

---

## 19. Technology Architecture

A potential technical architecture would be:

**React Frontend**

↓

**Django REST API**

↓

**Core Tuviora Services**

* Authentication
* Event Management
* Registration
* Ticketing
* Payments
* Team Management
* Communication
* Check-In

↓

**PostgreSQL Database**

External integrations would include:

**Africa's Talking**

* SMS
* USSD
* Voice services where required

**Payment Provider — MarzPay**

* Mobile Money
* Card payments
* Payment verification/webhooks

The backend should receive payment and communication callbacks through secure APIs and webhooks.

See [Architecture](../architecture/README.md) for how this maps onto the current implementation.

---

## 20. Project Goal

The goal of Tuviora is to make event organization simpler by combining registration, payments, attendee management and communication within one platform.

Tuviora aims to reduce the administrative burden on organizers while making event information and communication accessible to attendees through both internet and mobile channels.

---

## 21. Product Vision

Tuviora should eventually become an **event operating platform** rather than simply an event listing website.

Its long-term vision is to support the complete event lifecycle:

**Create → Register → Pay → Communicate → Attend → Check In → Analyse**

The initial MVP should focus on delivering this journey reliably before expanding into broader event discovery and advanced event-management functionality.
