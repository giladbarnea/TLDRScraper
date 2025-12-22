---
created: 2025-12-22 21:44
last_updated: 2025-12-22 19:44
---
# Discussion: Zen Overlay Header and Swipe Interactions

Here is the comprehensive redesign strategy for the **Zen Overlay**, integrating our refined interaction model, gestures, and the "To-Do" mental model.

### **Zen Overlay Redesign Strategy**

**Design Goal:** Shift the header from a rigid system navigation bar to an organic, functional control center that respects the user's "To-Do" mental model (Save for Later vs. Mark as Done).

---

### **1. Remove the Title from the Header**

Since the article title (e.g., *"Evaluating Context Compression..."*) is already the main H1 in the content area, remove it from the top bar entirely.

* **Why:** It reduces visual noise and lets the content breathe.
* **The Organic Feel:** It mimics a physical sheet of paper or a magazine where the headline is part of the page flow, not a sticky label duplicated on top.

### **2. Replace "Title" with "Source Context"**

In your hierarchy (*Day > Source > Article*), the "Zen" view isolates the Article. The missing context is the **Source**.

* **New Design:** Place the **Source Icon** (favicon) and **Source Name** (e.g., "Factory") in the center of the header.
* **Styling:** Use a smaller, lighter sans-serif font (e.g., grey/muted). It should feel like a "metadata tag" rather than a loud heading.
* **Delightful Detail:** Add the "Reading Time" next to the source (e.g., *"Factory • 4 min read"*).

### **3. Interaction Model: Distinguish "Pausing" from "Completing"**

We must distinguish between "putting the article back on the pile" (Collapse) and "checking it off the list" (Done). The header and gestures should map to these two distinct physical actions.

**A. The Controls (Header)**

* **Top Left: The Down Chevron (Vee).**
* *Action:* Collapses the modal. The article remains in your list.
* *Metaphor:* "I am putting this sheet back down." The arrow points down, signaling vertical movement (an overlay closing), not lateral navigation history.


* **Top Right: The Checkmark (Checkmark).**
* *Action:* Marks the article as "Read," closes the modal, and removes it from the parent list.
* *Metaphor:* "I am checking this off my to-do list."



**B. The Gestures (Delight)**

* **Swipe Down (Gravity):** Pulling down on the header (or the top of the content) acts just like the Down Chevron. The card slides away, saving the item for later.
* **Overscroll Up (Completion):** When the user reaches the bottom of the text, they can keep dragging up (overscroll). A checkmark icon appears/fills in the empty footer space. Releasing it triggers the "Mark as Done" action.

### **4. Soften the Boundaries (The "Organic" Look)**

The hard line separating the header from the content is rigid and kills the immersion.

* **Transparency:** Make the header background slightly transparent with a backdrop blur (frosted glass). This lets the content scroll "behind" it, making the UI feel layered and fluid.
* **Scroll Behavior:**
* **State A (Top):** No border, totally transparent background. The header elements float directly above the white page.
* **State B (Scrolled):** As the user scrolls down, the header background fades in (blur) to separate the controls from the text.


* **Gesture Integration:** The header is not just a visual strip; it is the physical **"handle"** of the card.
* Because the header visually floats (State A), the user perceives the header and the content as *one single sheet*.
* This encourages the **Swipe Down** gesture naturally—grabbing the "top of the paper" to pull it away feels intuitive.



---

### **Visualizing the Proposed Header**

**Current:**
`[ < ] [ Evaluating Context Comp... ]` (Hard bottom border)

**Proposed (Organic/Zen):**

`[ ⌄ ]       [ (Logo) Factory • 4 min ]       [ ✓ ]`

*(State A: Floating on white | State B: Frosted Glass)*

* **Left:** A discrete **Down Chevron** (Save for later / Collapse).
* **Center:** The **Source Metadata** (Anchors the user context).
* **Right:** An elegant **Checkmark** (Mark Done / Remove).
* **Below:** The body content begins with the massive Serif H1 Title.