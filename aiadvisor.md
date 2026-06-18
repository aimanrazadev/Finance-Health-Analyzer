Create a GPT-like chatbot UI for my AI advisor page.

Use only this stack:

Frontend: React
Backend: FastAPI only if backend integration is required
Database: MySQL only if backend/database changes are required
Styling: Tailwind CSS if already used, otherwise existing CSS
Charts: Recharts only if chart output is required
Icons: lucide-react
u can use shadcn/ui, framer-motion if needed

Do not add Next.js, Redux, Zustand, Prisma, MongoDB, Firebase, Supabase, or any new UI library unless it already exists in the project.


Important design direction:

The chatbot UI should look very similar to the provided screenshot/pasted chatbot component:

* Centered full-page AI chat screen
* Large heading at the top
* Small subtitle below heading
* Large rounded input box in the center
* Bottom action row inside the input card
* Attachment button on left
* Command button on left
* Send button on right
* Suggested prompt/action chips below the input
* Dark premium background
* Soft purple/black ambient background
* Minimal, calm, futuristic AI interface

Only follow AGENTS.md for font and typography rules:

* Use Inter, Geist, Manrope, or existing app font
* Use thin premium typography
* Use font-weight 300, 400, 500 mostly
* Avoid heavy bold text
* Keep text clean, soft, and minimal
* Use tabular numbers where financial numbers appear

Do NOT force the full AGENTS.md color palette here.
For this chatbot screen, keep the screenshot-like dark AI style.

Main page layout:

* Full-screen centered chatbot page
* Background should be very dark, close to black:

  * #07070A
  * #0A0A0F
  * #0D0B12
* Add a very subtle purple/indigo radial glow in the center/background
* Glow must be soft and low opacity
* Do not make it bright or childish
* The UI should feel premium, not neon

Header:
Title:
“How can I help with your finances?”

Subtitle:
“Ask about spending, savings, subscriptions, or financial health.”

Title style:

* Center aligned
* Font size around 34px to 40px
* Font weight 400 or 500
* Color: rgba(255,255,255,0.78)
* Letter spacing slightly tight
* No heavy bold

Subtitle style:

* Font size 15px to 16px
* Font weight 400
* Color: rgba(255,255,255,0.38)

Main chat input card:

* Width around 760px to 860px on desktop
* Rounded corners: 18px to 22px
* Background: rgba(255,255,255,0.025) or #121017
* Border: 1px solid rgba(255,255,255,0.08)
* Very soft shadow
* No strong border
* No bright gradient border
* No glassmorphism-heavy blur
* Keep the card clean and close to the screenshot

Textarea:

* Large textarea area
* Min height around 110px to 130px
* Transparent background
* No visible inner border
* Placeholder:
  “Ask about your spending, savings, or subscriptions…”
* Placeholder color: rgba(255,255,255,0.28)
* Text color: rgba(255,255,255,0.86)
* Font size: 15px
* Resize disabled
* Auto height if already implemented

Bottom toolbar inside input card:

* Border top: 1px solid rgba(255,255,255,0.06)
* Padding: 16px to 20px
* Left side: attachment button and command button
* Right side: send button

Toolbar icon buttons:

* Size around 42px x 42px
* Rounded: 10px to 12px
* Background: rgba(255,255,255,0.045)
* Hover background: rgba(255,255,255,0.075)
* Icon color: rgba(255,255,255,0.48)
* Hover icon color: rgba(255,255,255,0.75)
* Use lucide-react icons only
* Use strokeWidth around 1.6

Send button:

* Rounded: 10px to 12px
* Height around 44px
* Padding horizontal around 18px
* Disabled state: rgba(255,255,255,0.055), muted text
* Active state: rgba(255,255,255,0.12), text rgba(255,255,255,0.82)
* Keep it subtle like the screenshot
* Do not use bright green send button on this chatbot screen

Suggested prompt chips below input:
Replace generic UI commands with finance prompts.

Use these chips:

1. “Save more”
2. “Find overspending”
3. “Show subscriptions”
4. “Generate report”

Optional additional chips if space allows:
5. “Search transactions”
6. “Improve health score”

Chip style:

* Small rounded pills/cards
* Height around 42px to 46px
* Background: rgba(255,255,255,0.025)
* Border: 1px solid rgba(255,255,255,0.07)
* Text color: rgba(255,255,255,0.58)
* Hover background: rgba(255,255,255,0.055)
* Hover text: rgba(255,255,255,0.82)
* Icons from lucide-react
* Keep spacing like the screenshot

Chat behavior:

* Enter sends message
* Shift + Enter creates a new line
* Send button disabled if input is empty
* Clear input after sending
* Show loading state after sending:
  “Analyzing your financial data…”
* Keep messages in React local state
* If backend endpoint exists, call POST /advisor/ask
* If backend endpoint does not exist, create a clean placeholder function that can later connect to FastAPI

Backend request shape if integrated:

POST /advisor/ask

Request:
{
"message": "How can I save more money?",
"chat_id": optional
}

Expected response:
{
"summary": "...",
"main_problem": "...",
"recommendations": [
{
"title": "...",
"reason": "...",
"impact": "..."
}
],
"subscriptions": [],
"risk_note": "..."
}

When messages appear:

* User message should align right
* Assistant response should align left
* Assistant response should be displayed as clean financial answer cards, not basic chat bubbles
* Keep message width controlled and readable
* Do not make it look like WhatsApp, Discord, Slack, or customer support chat

Assistant response card sections:

* Summary
* Main issue
* Recommended actions
* Expected savings impact
* Related subscriptions
* Risk note

Example user prompts:

* “How can I save more money?”
* “Where am I overspending?”
* “Show all Zomato transactions above ₹500 from March.”
* “Generate my July spending report.”
* “Which subscriptions should I cancel?”
* “How can I improve my financial health score?”

If adapting the pasted AnimatedAIChat component:

* Keep the same centered GPT-like layout
* Keep the large input box style
* Keep the bottom toolbar style
* Keep the suggestion chips style
* Replace “How can I help today?” with “How can I help with your finances?”
* Replace “Type a command or ask a question” with “Ask about spending, savings, subscriptions, or financial health.”
* Replace “Ask zap a question…” with “Ask about your spending, savings, or subscriptions…”
* Replace Clone UI, Import Figma, Create Page, Improve with finance suggestions
* Remove unused imports
* Remove UI-specific command names
* Keep the visual direction close to the screenshot
* Do not redesign it into the dashboard card theme
* Use only AGENTS.md typography/font style

Do not touch:

* Authentication
* Dashboard
* Transactions
* Categories
* MySQL schema
* FastAPI routes

unless required only for connecting the chatbot.

Final output should be a clean React chatbot UI component that matches the screenshot style, uses the existing stack, and feels like a premium finance-focused GPT interface.
