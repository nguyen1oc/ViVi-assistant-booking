# Request Booking Access Tool

## Description
Open the booking email input when the user requests booking access without supplying an email. When an email is supplied, create an OTP challenge for `lookup`, `reschedule`, `cancel`, `update_details`, or `update_notifications`.
The OTP expires after 5 minutes, allows up to 5 attempts, and has a resend cooldown. These values are configurable.

## Parameters
- `booking_code` (optional): Existing booking code. Use only when the user provides it.
- `contact_value` (optional): Registered email address used to match the booking and receive OTP. Omit it when the user has expressed the booking-management intent but has not supplied an email; the tool then instructs the browser to show the email form.
- `purpose`: One of `lookup`, `reschedule`, `cancel`, `update_details`, `update_notifications`, or `manage`.
  `manage` grants read + reschedule + cancel in a single OTP session (used by the lookup screen).
- `preferred_channel`: OTP channel. Set to `email`.

## Security
Without `contact_value`, no OTP is created and the response contains only a UI directive. With `contact_value`, the response only contains a masked destination. The raw OTP is not stored or returned by this tool.
