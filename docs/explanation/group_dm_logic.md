# Group of decision makers

## SocketIO
Low-latency, bidirectional and event-based communication between a client and a server.
Flow chart of interations between server and clients: https://miro.com/app/board/uXjVKplY5co=/?shareablePresentation=1

Server: 
- File location: 
```json 
desdeo-webui:socketIoHandler.js 
```
- How it is injected:
```json 
desdeo-webui:server.js
```
- Runs on the same port as webui
- Emitters:
  ```json
  socket.emit("message", { message: "..." });
  ```
  - 'message': Send messages to the client
  ```json
  socket.emit(`execute-${action}`, requestIds);
  ```
  - `execute-${action}`: tell the client to execute the action (do interaction with the API side)
  ```json
  socket.emit(`executed-action`, action, requestIds);
  ```
  - `executed-action`: tell the client that the action has been done and executed successfully
  ```json
  socket.emit(`executing-${action}`, { message: "..." });
  ```
  - `executing-${action}`: tell the client that the action is being executed
- Listeners:
  ```json
  socket.on("message", (message: string) => {...});
  ```
  - 'message': receive messages from clients
  ```json
  socket.on("join-room", (username: string, roomID: string) => {...});
  ```
  - 'join-room': assign the client to a room that has the given room id
  ```json
  socket.on("leave-room", (username: string, roomID: string) => {...});
  ```
  - 'leave-room': withdraw the client from the room that has the given room id
  ```json
  socket.on("add-action", (action: string, requestId: number) => {...});
  ```
  - 'add-action':
    - If the action is 'initialize'
      - send event `execute-${action}` to the client if no others in the same room are executing this action
      - send event `executed-${action}` to the client if the action has been executed successfully
    (The above checking to avoid multiple users initialize the action simultaneously -> which leads to duplicate starting solutions)
    - If the action is other than 'initialize'
      - Record the id of the saved request according to the client id
      - Check if all other people in the same room has added the same action
        - If yes, send event `execute-${action}` to the client
        - If no, sending event `execute-${action}` to the client after 10 minutes waiting, unless others added the same action before the timeout period
  ```json
  socket.on("failed-action", (action: string) => {...});
  ```
  - 'failed-action': Received when the process, which is run by the client when receiving event `execute-${action}`, failed.
      The server just simply emits 'message' to others in the same room that the process failed
  ```json
  socket.on("finish-action", (action: string) => {...});
  ```
  - 'finish-action': Emits event `executed-action` to others in the same room
  ```json
  socket.on("disconnect", () => {...});
  ```
  - 'disconnect': When the client is disconnected from the server

Client:
- File location: 
```json 
desdeo-webui:src/hooks.client.ts
```
- How it is started:
```json 
Code in client hooks will run when the application starts up
```
- Emitters:
  ```json
  socket.emit("message", { message: "..." });
  ```
  - 'message': Send messages to Server
  ```json
  socketVal.emit("join-room", $username, "problem-" + $prblemId);
  ```
  - 'join-room': Send event to join a room with the room id that indicates problem id that the client wants to solve (src/routes/solve/+page.svelte)
  ```json
  socketVal.emit("leave-room", $username, "problem-" + $prblemId);
  ```
  - 'leave-room': Send event to leave room with the room id that indicates problem id that the client is solving (src/routes/solve/+page.svelte)
  ```json
  socketVal.emit("add-action", action, requestId);
  ```
  - 'add-action': Send event to add action with type of action and the id of the saved request in method-state table
  ```json
  socketVal.emit("failed-action", action);
  ```
  - 'failed-action': Send event to tell server that the action has not executed successfully
  ```json
  socketVal.emit("finish-action", action);
  ```
  - 'finish-action': Send event to tell server that the action has been done and executed successfully
- Listeners:
  ```json
  socket.on("message", (message: string) => {...});
  ```
  - 'message': Receive messages sent from the Server
  ```json
  socket.on("execute-" + action, (requestIds: number[]) => {...});
  ```
  - `execute-${action}`: execute the action with given saved requests' ids
  ```json
  socket.on("executed-action", (action: string, requestIds: number[]) => {...});
  ```
  - `executed-action`: fetch generated cached results for the action
  ```json
  socket.on("executing-action", (action: string) => {...});
  ```
  - `executing-${action}`: the client stops listening to event `execute-${action}`

## UI interaction

On UI, when an action is fired/clicked (Iterate / Vote / initialize), the handler of the action is not called, handle_caller() is called instead
handle_caller()
1st - Add one-time listener `execute-${action}` to SocketIO client
```json
socketVal.off("execute-" + action).once("execute-" + action, executeAction);
```
  - When the server emits `execute-${action}`, the client runs API
    - If the API is successfully run, client emits 'finish-action'
    ```json
    socketVal.emit("finish-action", action);
    ```
    - If the API returns errors, client emits 'failed-action'
    ```json
    socketVal.emit("failed-action", action);
    ```
2nd - It saves action request on API side (method name, request type (iterate / vote / initialize), request params)
3rd - Emits event 'add-action' to SocketIO server
```json
socketVal.emit("add-action", action, requestId);
```
NOTE: 
- Action ``` initialize ``` doesn't save action request on API side

## Solution voting

After each iteration, several solutions will be generated. Therefore, DMs need to vote for their own favorite solution among these solutions.
Based on all DMs' vote, the app will determine the next solving step.

All solutions generated from iteration / intermediate process are marked as 'current' ``` current=True ```
After counting voting, these cases will happen: (router path: /solution-vote)
- Case 1: If DMs all vote for 1 single solution
  - The solution is set as the only 'current' and also as 'to_vote' ``` current=True, to_vote=True ```
- Case 2: If among the votes, there are 2 most selected solutions
  - An intermediate solution is generated and marked as the only 'current' ``` current=True ```
- Case 3: There are more than 2 most selected solutions

Which is the next solving step ?
- If there is 'chosen' solution ``` chosen=True ```
  - The app shows the final solution. the problem ends
- If there is 'to_vote' solution ``` to_vote=True ```
  - Ask if they all want to choose this solution as final (router path: /final-solution-vote)
    - If yes, this solution is marked as 'chosen' and the problem ends ``` chosen=True ```
    - If no, this solution is the reference_solution for next iteration ``` json current=True ```
- If there is 1 single 'current' solution ``` len(current=True) == 1 ```
  - The app lets the DMs to continue the iteration with this solution
- If there are more than 1 'current' solution ``` len(current=True) > 1 ```
  - The voting process is repeated until it falls into above-mentioned Case 1 or 2

Note:
- Without ``` to_vote ```, the DM, who happens to refresh access token or has to log in again, can't see the voting options if there are any.


