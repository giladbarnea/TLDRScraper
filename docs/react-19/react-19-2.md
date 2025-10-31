---
last-updated: 2025-10-31 11:03, 2fad697
---

Title: React 19.2 – React

URL Source: https://react.dev/blog/2025/10/01/react-19-2

Published Time: Thu, 30 Oct 2025 16:47:06 GMT

Markdown Content:
October 1, 2025 by [The React Team](https://react.dev/community/team)

* * *

React 19.2 is now available on npm!

This is our third release in the last year, following React 19 in December and React 19.1 in June. In this post, we’ll give an overview of the new features in React 19.2, and highlight some notable changes.

*   [New React Features](https://react.dev/blog/2025/10/01/react-19-2#new-react-features)
    *   [`<Activity />`](https://react.dev/blog/2025/10/01/react-19-2#activity)
    *   [`useEffectEvent`](https://react.dev/blog/2025/10/01/react-19-2#use-effect-event)
    *   [`cacheSignal`](https://react.dev/blog/2025/10/01/react-19-2#cache-signal)
    *   [Performance Tracks](https://react.dev/blog/2025/10/01/react-19-2#performance-tracks)

*   [New React DOM Features](https://react.dev/blog/2025/10/01/react-19-2#new-react-dom-features)
    *   [Partial Pre-rendering](https://react.dev/blog/2025/10/01/react-19-2#partial-pre-rendering)

*   [Notable Changes](https://react.dev/blog/2025/10/01/react-19-2#notable-changes)
    *   [Batching Suspense Boundaries for SSR](https://react.dev/blog/2025/10/01/react-19-2#batching-suspense-boundaries-for-ssr)
    *   [SSR: Web Streams support for Node](https://react.dev/blog/2025/10/01/react-19-2#ssr-web-streams-support-for-node)
    *   [`eslint-plugin-react-hooks` v6](https://react.dev/blog/2025/10/01/react-19-2#eslint-plugin-react-hooks)
    *   [Update the default `useId` prefix](https://react.dev/blog/2025/10/01/react-19-2#update-the-default-useid-prefix)

*   [Changelog](https://react.dev/blog/2025/10/01/react-19-2#changelog)

* * *

New React Features [](https://react.dev/blog/2025/10/01/react-19-2#new-react-features "Link for New React Features ")
---------------------------------------------------------------------------------------------------------------------

### `<Activity />`[](https://react.dev/blog/2025/10/01/react-19-2#activity "Link for this heading")

`<Activity>` lets you break your app into “activities” that can be controlled and prioritized.

You can use Activity as an alternative to conditionally rendering parts of your app:

`// Before{isVisible && <Page />}// After<Activity mode={isVisible ? 'visible' : 'hidden'}><Page /></Activity>`

In React 19.2, Activity supports two modes: `visible` and `hidden`.

*   `hidden`: hides the children, unmounts effects, and defers all updates until React has nothing left to work on.
*   `visible`: shows the children, mounts effects, and allows updates to be processed normally.

This means you can pre-render and keep rendering hidden parts of the app without impacting the performance of anything visible on screen.

You can use Activity to render hidden parts of the app that a user is likely to navigate to next, or to save the state of parts the user navigates away from. This helps make navigations quicker by loading data, css, and images in the background, and allows back navigations to maintain state such as input fields.

In the future, we plan to add more modes to Activity for different use cases.

For examples on how to use Activity, check out the [Activity docs](https://react.dev/reference/react/Activity).

* * *

### `useEffectEvent`[](https://react.dev/blog/2025/10/01/react-19-2#use-effect-event "Link for this heading")

One common pattern with `useEffect` is to notify the app code about some kind of “events” from an external system. For example, when a chat room gets connected, you might want to display a notification:

`function ChatRoom({ roomId, theme }) {useEffect(() => {const connection = createConnection(serverUrl, roomId);connection.on('connected', () => {showNotification('Connected!', theme);});connection.connect();return () => {connection.disconnect()};}, [roomId, theme]);// ...`

The problem with the code above is that a change to any values used inside such an “event” will cause the surrounding Effect to re-run. For example, changing the `theme` will cause the chat room to reconnect. This makes sense for values related to the Effect logic itself, like `roomId`, but it doesn’t make sense for `theme`.

To solve this, most users just disable the lint rule and exclude the dependency. But that can lead to bugs since the linter can no longer help you keep the dependencies up to date if you need to update the Effect later.

With `useEffectEvent`, you can split the “event” part of this logic out of the Effect that emits it:

`function ChatRoom({ roomId, theme }) {const onConnected = useEffectEvent(() => {showNotification('Connected!', theme);});useEffect(() => {const connection = createConnection(serverUrl, roomId);connection.on('connected', () => {onConnected();});connection.connect();return () => connection.disconnect();}, [roomId]); // ✅ All dependencies declared (Effect Events aren't dependencies)// ...`

Similar to DOM events, Effect Events always “see” the latest props and state.

**Effect Events should _not_ be declared in the dependency array**. You’ll need to upgrade to `eslint-plugin-react-hooks@latest` so that the linter doesn’t try to insert them as dependencies. Note that Effect Events can only be declared in the same component or Hook as “their” Effect. These restrictions are verified by the linter.

### Note

#### When to use `useEffectEvent`[](https://react.dev/blog/2025/10/01/react-19-2#when-to-use-useeffectevent "Link for this heading")

You should use `useEffectEvent` for functions that are conceptually “events” that happen to be fired from an Effect instead of a user event (that’s what makes it an “Effect Event”). You don’t need to wrap everything in `useEffectEvent`, or to use it just to silence the lint error, as this can lead to bugs.

For a deep dive on how to think about Event Effects, see: [Separating Events from Effects](https://react.dev/learn/separating-events-from-effects#extracting-non-reactive-logic-out-of-effects).

* * *

### `cacheSignal`[](https://react.dev/blog/2025/10/01/react-19-2#cache-signal "Link for this heading")

`cacheSignal` allows you to know when the [`cache()`](https://react.dev/reference/react/cache) lifetime is over:

`import {cache, cacheSignal} from 'react';const dedupedFetch = cache(fetch);async function Component() {await dedupedFetch(url, { signal: cacheSignal() });}`

This allows you to clean up or abort work when the result will no longer be used in the cache, such as:

*   React has successfully completed rendering
*   The render was aborted
*   The render has failed

For more info, see the [`cacheSignal` docs](https://react.dev/reference/react/cacheSignal).

* * *

### Performance Tracks [](https://react.dev/blog/2025/10/01/react-19-2#performance-tracks "Link for Performance Tracks ")

React 19.2 adds a new set of [custom tracks](https://developer.chrome.com/docs/devtools/performance/extension) to Chrome DevTools performance profiles to provide more information about the performance of your React app:

The [React Performance Tracks docs](https://react.dev/reference/dev-tools/react-performance-tracks) explain everything included in the tracks, but here is a high-level overview.

#### Scheduler ⚛ [](https://react.dev/blog/2025/10/01/react-19-2#scheduler- "Link for Scheduler ⚛ ")

The Scheduler track shows what React is working on for different priorities such as “blocking” for user interactions, or “transition” for updates inside startTransition. Inside each track, you will see the type of work being performed such as the event that scheduled an update, and when the render for that update happened.

We also show information such as when an update is blocked waiting for a different priority, or when React is waiting for paint before continuing. The Scheduler track helps you understand how React splits your code into different priorities, and the order it completed the work.

See the [Scheduler track](https://react.dev/reference/dev-tools/react-performance-tracks#scheduler) docs to see everything included.

#### Components ⚛ [](https://react.dev/blog/2025/10/01/react-19-2#components- "Link for Components ⚛ ")

The Components track shows the tree of components that React is working on either to render or run effects. Inside you’ll see labels such as “Mount” for when children mount or effects are mounted, or “Blocked” for when rendering is blocked due to yielding to work outside React.

The Components track helps you understand when components are rendered or run effects, and the time it takes to complete that work to help identify performance problems.

See the [Components track docs](https://react.dev/reference/dev-tools/react-performance-tracks#components) for see everything included.

* * *

New React DOM Features [](https://react.dev/blog/2025/10/01/react-19-2#new-react-dom-features "Link for New React DOM Features ")
---------------------------------------------------------------------------------------------------------------------------------

### Partial Pre-rendering [](https://react.dev/blog/2025/10/01/react-19-2#partial-pre-rendering "Link for Partial Pre-rendering ")

In 19.2 we’re adding a new capability to pre-render part of the app ahead of time, and resume rendering it later.

This feature is called “Partial Pre-rendering”, and allows you to pre-render the static parts of your app and serve it from a CDN, and then resume rendering the shell to fill it in with dynamic content later.

To pre-render an app to resume later, first call `prerender` with an `AbortController`:

`const {prelude, postponed} = await prerender(<App />, {signal: controller.signal,});// Save the postponed state for laterawait savePostponedState(postponed);// Send prelude to client or CDN.`

Then, you can return the `prelude` shell to the client, and later call `resume` to “resume” to a SSR stream:

`const postponed = await getPostponedState(request);const resumeStream = await resume(<App />, postponed);// Send stream to client.`

Or you can call `resumeAndPrerender` to resume to get static HTML for SSG:

`const postponedState = await getPostponedState(request);const { prelude } = await resumeAndPrerender(<App />, postponedState);// Send complete HTML prelude to CDN.`

For more info, see the docs for the new APIs:

*   `react-dom/server`
    *   [`resume`](https://react.dev/reference/react-dom/server/resume): for Web Streams.
    *   [`resumeToPipeableStream`](https://react.dev/reference/react-dom/server/resumeToPipeableStream) for Node Streams.

*   `react-dom/static`
    *   [`resumeAndPrerender`](https://react.dev/reference/react-dom/static/resumeAndPrerender) for Web Streams.
    *   [`resumeAndPrerenderToNodeStream`](https://react.dev/reference/react-dom/static/resumeAndPrerenderToNodeStream) for Node Streams.

Additionally, the prerender apis now return a `postpone` state to pass to the `resume` apis.

* * *

Notable Changes [](https://react.dev/blog/2025/10/01/react-19-2#notable-changes "Link for Notable Changes ")
------------------------------------------------------------------------------------------------------------

### Batching Suspense Boundaries for SSR [](https://react.dev/blog/2025/10/01/react-19-2#batching-suspense-boundaries-for-ssr "Link for Batching Suspense Boundaries for SSR ")

We fixed a behavioral bug where Suspense boundaries would reveal differently depending on if they were rendered on the client or when streaming from server-side rendering.

Starting in 19.2, React will batch reveals of server-rendered Suspense boundaries for a short time, to allow more content to be revealed together and align with the client-rendered behavior.

![Image 1: Diagram with three sections, with an arrow transitioning each section in between. The first section contains a page rectangle showing a glimmer loading state with faded bars. The second panel shows the top half of the page revealed and highlighted in blue. The third panel shows the entire the page revealed and highlighted in blue.](https://react.dev/_next/image?url=%2Fimages%2Fdocs%2Fdiagrams%2F19_2_batching_before.dark.png&w=3840&q=75)

![Image 2: Diagram with three sections, with an arrow transitioning each section in between. The first section contains a page rectangle showing a glimmer loading state with faded bars. The second panel shows the top half of the page revealed and highlighted in blue. The third panel shows the entire the page revealed and highlighted in blue.](https://react.dev/_next/image?url=%2Fimages%2Fdocs%2Fdiagrams%2F19_2_batching_before.png&w=3840&q=75)

Previously, during streaming server-side rendering, suspense content would immediately replace fallbacks.

![Image 3: Diagram with three sections, with an arrow transitioning each section in between. The first section contains a page rectangle showing a glimmer loading state with faded bars. The second panel shows the same page. The third panel shows the entire the page revealed and highlighted in blue.](https://react.dev/_next/image?url=%2Fimages%2Fdocs%2Fdiagrams%2F19_2_batching_after.dark.png&w=3840&q=75)

![Image 4: Diagram with three sections, with an arrow transitioning each section in between. The first section contains a page rectangle showing a glimmer loading state with faded bars. The second panel shows the same page. The third panel shows the entire the page revealed and highlighted in blue.](https://react.dev/_next/image?url=%2Fimages%2Fdocs%2Fdiagrams%2F19_2_batching_after.png&w=3840&q=75)

In React 19.2, suspense boundaries are batched for a small amount of time, to allow revealing more content together.

This fix also prepares apps for supporting `<ViewTransition>` for Suspense during SSR. By revealing more content together, animations can run in larger batches of content, and avoid chaining animations of content that stream in close together.

### Note

React uses heuristics to ensure throttling does not impact core web vitals and search ranking.

For example, if the total page load time is approaching 2.5s (which is the time considered “good” for [LCP](https://web.dev/articles/lcp)), React will stop batching and reveal content immediately so that the throttling is not the reason to miss the metric.

* * *

### SSR: Web Streams support for Node [](https://react.dev/blog/2025/10/01/react-19-2#ssr-web-streams-support-for-node "Link for SSR: Web Streams support for Node ")

React 19.2 adds support for Web Streams for streaming SSR in Node.js:

*   [`renderToReadableStream`](https://react.dev/reference/react-dom/server/renderToReadableStream) is now available for Node.js
*   [`prerender`](https://react.dev/reference/react-dom/static/prerender) is now available for Node.js

As well as the new `resume` APIs:

*   [`resume`](https://react.dev/reference/react-dom/server/resume) is available for Node.js.
*   [`resumeAndPrerender`](https://react.dev/reference/react-dom/static/resumeAndPrerender) is available for Node.js.

* * *

### `eslint-plugin-react-hooks` v6 [](https://react.dev/blog/2025/10/01/react-19-2#eslint-plugin-react-hooks "Link for this heading")

We also published `eslint-plugin-react-hooks@latest` with flat config by default in the `recommended` preset, and opt-in for new React Compiler powered rules.

To continue using the legacy config, you can change to `recommended-legacy`:

`- extends: ['plugin:react-hooks/recommended']+ extends: ['plugin:react-hooks/recommended-legacy']`

For a full list of compiler enabled rules, [check out the linter docs](https://react.dev/reference/eslint-plugin-react-hooks#recommended).

Check out the `eslint-plugin-react-hooks`[changelog for a full list of changes](https://github.com/facebook/react/blob/main/packages/eslint-plugin-react-hooks/CHANGELOG.md#610).

* * *

### Update the default `useId` prefix [](https://react.dev/blog/2025/10/01/react-19-2#update-the-default-useid-prefix "Link for this heading")

In 19.2, we’re updating the default `useId` prefix from `:r:` (19.0.0) or `«r»` (19.1.0) to `_r_`.

The original intent of using a special character that was not valid for CSS selectors was that it would be unlikely to collide with IDs written by users. However, to support View Transitions, we need to ensure that IDs generated by `useId` are valid for `view-transition-name` and XML 1.0 names.

* * *

Changelog [](https://react.dev/blog/2025/10/01/react-19-2#changelog "Link for Changelog ")
------------------------------------------------------------------------------------------

Other notable changes

*   `react-dom`: Allow nonce to be used on hoistable styles [#32461](https://github.com/facebook/react/pull/32461)
*   `react-dom`: Warn for using a React owned node as a Container if it also has text content [#32774](https://github.com/facebook/react/pull/32774)

Notable bug fixes

*   `react`: Stringify context as “SomeContext” instead of “SomeContext.Provider” [#33507](https://github.com/facebook/react/pull/33507)
*   `react`: Fix infinite useDeferredValue loop in popstate event [#32821](https://github.com/facebook/react/pull/32821)
*   `react`: Fix a bug when an initial value was passed to useDeferredValue [#34376](https://github.com/facebook/react/pull/34376)
*   `react`: Fix a crash when submitting forms with Client Actions [#33055](https://github.com/facebook/react/pull/33055)
*   `react`: Hide/unhide the content of dehydrated suspense boundaries if they resuspend [#32900](https://github.com/facebook/react/pull/32900)
*   `react`: Avoid stack overflow on wide trees during Hot Reload [#34145](https://github.com/facebook/react/pull/34145)
*   `react`: Improve component stacks in various places [#33629](https://github.com/facebook/react/pull/33629), [#33724](https://github.com/facebook/react/pull/33724), [#32735](https://github.com/facebook/react/pull/32735), [#33723](https://github.com/facebook/react/pull/33723)
*   `react`: Fix a bug with React.use inside React.lazy-ed Component [#33941](https://github.com/facebook/react/pull/33941)
*   `react-dom`: Stop warning when ARIA 1.3 attributes are used [#34264](https://github.com/facebook/react/pull/34264)
*   `react-dom`: Fix a bug with deeply nested Suspense inside Suspense fallbacks [#33467](https://github.com/facebook/react/pull/33467)
*   `react-dom`: Avoid hanging when suspending after aborting while rendering [#34192](https://github.com/facebook/react/pull/34192)

For a full list of changes, please see the [Changelog](https://github.com/facebook/react/blob/main/CHANGELOG.md).

* * *

_Thanks to [Ricky Hanlon](https://bsky.app/profile/ricky.fm) for [writing this post](https://www.youtube.com/shorts/T9X3YkgZRG0), [Dan Abramov](https://bsky.app/profile/danabra.mov), [Matt Carroll](https://twitter.com/mattcarrollcode), [Jack Pope](https://jackpope.me/), and [Joe Savona](https://x.com/en\_JS) for reviewing this post._
