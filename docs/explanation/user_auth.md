# User Authentication

Authentication is granted with access and refresh tokens. Once the user's username and password are validated, the backend generates tokens and sends them to the UI.
By virtue of the fact that the refresh token is needed to generate new access token, like when the access token is not valid anymore or is not yet generated, 
the refresh token should have longer validity period than the access token.

## Authentication

The authentication is done via WebUI's server api route `api/signIn`, which sends the request to backend's `token` route.
After the backend responds to WebUI, the WebUI saves the refresh token in a cookie. 

By this way, the `refreshToken` cookie is saved with the same domain as the client's, since WebUI's server and client runs on the same domain. 
The domain is quite important property in making sure that the cookie persists after a page refresh.

## Access token

The token is used as Bearer authentication everytime the UI interacts with the backend.

## Refresh token

The `refresh` action can be requested via function `refreshToken()` in `webui::src/lib/api.ts`. This function calls WebUI's server api `api/refresh`
(The WebUI's server has the access to the cookies saved in the client's browser), that calls `refresh` in the backend, which returns the new valid
access token.

#### When `refresh` action is called ?

In `webui:src/hooks.client.ts`, there are interceptors for `fetch` and `axios` requests, which call `refresh` and then re-run the original request, if the original request faces error 401.

#### What happens if the `refresh` fails ?

The user is redirected to `/login` page.

## Why making use of WebUI's server routes, instead of calling backend directly?

`api/refresh`, `api/logout`: The WebUI's server has the access to the cookies saved in the client's browser.

`api/signIn`: WebUI's server and client runs on the same domain, so when being set in a WebUI's server route, the cookie has the same `domain` as the client's. 
The domain is quite important property in making sure that the cookie persists after a page refresh.

## Brainstorm

Should the refresh token be renewed after `refresh` action ?
