---
last_updated: 2025-11-14 16:24, 722a1a0
---
Title: use – React

URL Source: https://react.dev/reference/react/use

Markdown Content:
`use` is a React API that lets you read the value of a resource like a [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) or [context](https://react.dev/learn/passing-data-deeply-with-context).

`const value = use(resource);`

- [Reference](https://react.dev/reference/react/use#reference)
  - [`use(resource)`](https://react.dev/reference/react/use#use)
- [Usage](https://react.dev/reference/react/use#usage)
  - [Reading context with `use`](https://react.dev/reference/react/use#reading-context-with-use)
  - [Streaming data from the server to the client](https://react.dev/reference/react/use#streaming-data-from-server-to-client)
  - [Dealing with rejected Promises](https://react.dev/reference/react/use#dealing-with-rejected-promises)
- [Troubleshooting](https://react.dev/reference/react/use#troubleshooting)
  - [“Suspense Exception: This is not a real error!”](https://react.dev/reference/react/use#suspense-exception-error)

-----

## Reference [](https://react.dev/reference/react/use#reference)

### `use(resource)`[](https://react.dev/reference/react/use#use)

Call `use` in your component to read the value of a resource like a [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) or [context](https://react.dev/learn/passing-data-deeply-with-context).

`import { use } from 'react';function MessageComponent({ messagePromise }) {const message = use(messagePromise);const theme = use(ThemeContext);// ...`

Unlike React Hooks, `use` can be called within loops and conditional statements like `if`. Like React Hooks, the function that calls `use` must be a Component or Hook.

When called with a Promise, the `use` API integrates with [`Suspense`](https://react.dev/reference/react/Suspense) and [Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary). The component calling `use`*suspends* while the Promise passed to `use` is pending. If the component that calls `use` is wrapped in a Suspense boundary, the fallback will be displayed. Once the Promise is resolved, the Suspense fallback is replaced by the rendered components using the data returned by the `use` API. If the Promise passed to `use` is rejected, the fallback of the nearest Error Boundary will be displayed.

[See more examples below.](https://react.dev/reference/react/use#usage)

#### Parameters [](https://react.dev/reference/react/use#parameters)

- `resource`: this is the source of the data you want to read a value from. A resource can be a [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) or a [context](https://react.dev/learn/passing-data-deeply-with-context).

#### Returns [](https://react.dev/reference/react/use#returns)

The `use` API returns the value that was read from the resource like the resolved value of a [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) or [context](https://react.dev/learn/passing-data-deeply-with-context).

#### Caveats [](https://react.dev/reference/react/use#caveats)

- The `use` API must be called inside a Component or a Hook.
- When fetching data in a [Server Component](https://react.dev/reference/rsc/server-components), prefer `async` and `await` over `use`. `async` and `await` pick up rendering from the point where `await` was invoked, whereas `use` re-renders the component after the data is resolved.
- Prefer creating Promises in [Server Components](https://react.dev/reference/rsc/server-components) and passing them to [Client Components](https://react.dev/reference/rsc/use-client) over creating Promises in Client Components. Promises created in Client Components are recreated on every render. Promises passed from a Server Component to a Client Component are stable across re-renders. [See this example](https://react.dev/reference/react/use#streaming-data-from-server-to-client).

-----

## Usage [](https://react.dev/reference/react/use#usage)

### Reading context with `use`[](https://react.dev/reference/react/use#reading-context-with-use)

When a [context](https://react.dev/learn/passing-data-deeply-with-context) is passed to `use`, it works similarly to [`useContext`](https://react.dev/reference/react/useContext). While `useContext` must be called at the top level of your component, `use` can be called inside conditionals like `if` and loops like `for`. `use` is preferred over `useContext` because it is more flexible.

`import { use } from 'react';function Button() {const theme = use(ThemeContext);// ...`

`use` returns the context value for the context you passed. To determine the context value, React searches the component tree and finds **the closest context provider above** for that particular context.

To pass context to a `Button`, wrap it or one of its parent components into the corresponding context provider.

`function MyPage() {return (<ThemeContext value="dark"><Form /></ThemeContext>);}function Form() {// ... renders buttons inside ...}`

It doesn’t matter how many layers of components there are between the provider and the `Button`. When a `Button`*anywhere* inside of `Form` calls `use(ThemeContext)`, it will receive `"dark"` as the value.

Unlike [`useContext`](https://react.dev/reference/react/useContext), `use` can be called in conditionals and loops like `if`.

`function HorizontalRule({ show }) {if (show) {const theme = use(ThemeContext);return <hr className={theme} />;}return false;}`

`use` is called from inside a `if` statement, allowing you to conditionally read values from a Context.

### Pitfall

Like `useContext`, `use(context)` always looks for the closest context provider *above* the component that calls it. It searches upwards and **does not** consider context providers in the component from which you’re calling `use(context)`.

import { createContext, use } from ‘react’;

const ThemeContext = createContext(null);

export default function MyApp() {
return (
<ThemeContext value="dark">
<Form />
</ThemeContext>
)
}

function Form() {
return (
<Panel title="Welcome">
<Button show={true}>Sign up</Button>
<Button show={false}>Log in</Button>
</Panel>
);
}

function Panel({ title, children }) {
const theme = use(ThemeContext);
const className = ‘panel-’ + theme;
return (
<section className={className}>
<h1>{title}</h1>
{children}
</section>
)
}

function Button({ show, children }) {
if (show) {
const theme = use(ThemeContext);
const className = ‘button-’ + theme;
return (
<button className={className}>
{children}
</button>
);
}
return false
}

### Streaming data from the server to the client [](https://react.dev/reference/react/use#streaming-data-from-server-to-client)

Data can be streamed from the server to the client by passing a Promise as a prop from a Server Component to a Client Component.

`import { fetchMessage } from './lib.js';import { Message } from './message.js';export default function App() {const messagePromise = fetchMessage();return (<Suspense fallback={<p>waiting for message...</p>}><Message messagePromise={messagePromise} /></Suspense>);}`

The Client Component then takes the Promise it received as a prop and passes it to the `use` API. This allows the Client Component to read the value from the Promise that was initially created by the Server Component.

`// message.js'use client';import { use } from 'react';export function Message({ messagePromise }) {const messageContent = use(messagePromise);return <p>Here is the message: {messageContent}</p>;}`

Because `Message` is wrapped in [`Suspense`](https://react.dev/reference/react/Suspense), the fallback will be displayed until the Promise is resolved. When the Promise is resolved, the value will be read by the `use` API and the `Message` component will replace the Suspense fallback.

“use client”;

import { use, Suspense } from “react”;

function Message({ messagePromise }) {
const messageContent = use(messagePromise);
return <p>Here is the message: {messageContent}</p>;
}

export function MessageContainer({ messagePromise }) {
return (
<Suspense fallback={<p>⌛Downloading message…</p>}>
<Message messagePromise={messagePromise} />
</Suspense>
);
}

### Note

When passing a Promise from a Server Component to a Client Component, its resolved value must be serializable to pass between server and client. Data types like functions aren’t serializable and cannot be the resolved value of such a Promise.

##### Deep Dive

#### Should I resolve a Promise in a Server or Client Component? [](https://react.dev/reference/react/use#resolve-promise-in-server-or-client-component)

A Promise can be passed from a Server Component to a Client Component and resolved in the Client Component with the `use` API. You can also resolve the Promise in a Server Component with `await` and pass the required data to the Client Component as a prop.

`export default async function App() {const messageContent = await fetchMessage();return <Message messageContent={messageContent} />}`

But using `await` in a [Server Component](https://react.dev/reference/rsc/server-components) will block its rendering until the `await` statement is finished. Passing a Promise from a Server Component to a Client Component prevents the Promise from blocking the rendering of the Server Component.

### Dealing with rejected Promises [](https://react.dev/reference/react/use#dealing-with-rejected-promises)

In some cases a Promise passed to `use` could be rejected. You can handle rejected Promises by either:

1. [Displaying an error to users with an Error Boundary.](https://react.dev/reference/react/use#displaying-an-error-to-users-with-error-boundary)
1. [Providing an alternative value with `Promise.catch`](https://react.dev/reference/react/use#providing-an-alternative-value-with-promise-catch)

### Pitfall

`use` cannot be called in a try-catch block. Instead of a try-catch block [wrap your component in an Error Boundary](https://react.dev/reference/react/use#displaying-an-error-to-users-with-error-boundary), or [provide an alternative value to use with the Promise’s `.catch` method](https://react.dev/reference/react/use#providing-an-alternative-value-with-promise-catch).

#### Displaying an error to users with an Error Boundary [](https://react.dev/reference/react/use#displaying-an-error-to-users-with-error-boundary)

If you’d like to display an error to your users when a Promise is rejected, you can use an [Error Boundary](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary). To use an Error Boundary, wrap the component where you are calling the `use` API in an Error Boundary. If the Promise passed to `use` is rejected the fallback for the Error Boundary will be displayed.

“use client”;

import { use, Suspense } from “react”;
import { ErrorBoundary } from “react-error-boundary”;

export function MessageContainer({ messagePromise }) {
return (
<ErrorBoundary fallback={<p>⚠️Something went wrong</p>}>
<Suspense fallback={<p>⌛Downloading message…</p>}>
<Message messagePromise={messagePromise} />
</Suspense>
</ErrorBoundary>
);
}

function Message({ messagePromise }) {
const content = use(messagePromise);
return <p>Here is the message: {content}</p>;
}

#### Providing an alternative value with `Promise.catch`[](https://react.dev/reference/react/use#providing-an-alternative-value-with-promise-catch)

If you’d like to provide an alternative value when the Promise passed to `use` is rejected you can use the Promise’s [`catch`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/catch) method.

`import { Message } from './message.js';export default function App() {const messagePromise = new Promise((resolve, reject) => {reject();}).catch(() => {return "no new message found.";});return (<Suspense fallback={<p>waiting for message...</p>}><Message messagePromise={messagePromise} /></Suspense>);}`

To use the Promise’s `catch` method, call `catch` on the Promise object. `catch` takes a single argument: a function that takes an error message as an argument. Whatever is returned by the function passed to `catch` will be used as the resolved value of the Promise.

-----

## Troubleshooting [](https://react.dev/reference/react/use#troubleshooting)

### “Suspense Exception: This is not a real error!” [](https://react.dev/reference/react/use#suspense-exception-error)

You are either calling `use` outside of a React Component or Hook function, or calling `use` in a try–catch block. If you are calling `use` inside a try–catch block, wrap your component in an Error Boundary, or call the Promise’s `catch` to catch the error and resolve the Promise with another value. [See these examples](https://react.dev/reference/react/use#dealing-with-rejected-promises).

If you are calling `use` outside a React Component or Hook function, move the `use` call to a React Component or Hook function.

`function MessageComponent({messagePromise}) {function download() {// ❌ the function calling `use` is not a Component or Hookconst message = use(messagePromise);// ...`

Instead, call `use` outside any component closures, where the function that calls `use` is a Component or Hook.

`function MessageComponent({messagePromise}) {// ✅ `use` is being called from a component. const message = use(messagePromise);// ...`