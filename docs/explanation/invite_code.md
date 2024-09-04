# Invite code

## Requirements

- `invitee`: id of the user to be invited
- `problem_id`: id of the problem

## How to create code?

Location: <api_url>/docs

API: [POST] /invite

Firstly, it requires authorization on `docs`to be able to execute the API. After authorization, fill in the requirements, then execute the API.
The API will return the code in the response.

```json
{
  "code": "b85b0b0a7218a7b81725432803.580441"
}
```

## Where is the code stored?

The code is stored in `Invite` table. Each row in `Invite` table includes:
- `inviter`: the user that creates the code
- `invitee`: the user that is invited
- `problem_id`: the problem id associated with the code
- `code`: the invite code
- `date_created`: the date and time that the code is created

## How to login with the code?

The user can log in with the code at: `<webui_url>/$code`, in which `$code` is the invite code.

## What is really happening on the UI?

UI calls API `/login-with-invite`, which fetches the code's info from the db. With the invitee's id, the API responds 
to the UI with access and refresh tokens, and invitee's username, which are all needed to authenticate a user on UI.


## Further development

- Do we need `problem_id` value? For now, the `problem_id` value is not being used. It should be removed if it's not used at all.


