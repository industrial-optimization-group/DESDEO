# Websockets and Group Decision Making

This page documents how the Group Decision Making (GDM) framework built into DESDEO functions and how it utilizes websockets. This page also goes over how the functionality of this framework can be leveraged to create new GDM methods. For now, there is a functioning Group NIMBUS implementation, that we're going to be using as an example method to explain the concepts of this framework. In short, GNIMBUS is a group extension of the [NIMBUS](https://doi.org/10.1016/j.ejor.2004.07.052) method, in which a group articulates individual preferences, send them to the method and then vote for a solution.

A useful tool for working with websockets is [Websocketking](https://websocketking.com/). It allows creating multiple connections, saving payloads and more. Once a user enters the page for the first time, a quick introduction should begin, going into further details.

## Notes on the implementation
As with DESDEO in general, the endpoint routers and models used within are split into separate files. The relevant GDM models can be found at DESDEO/desdeo/api/models/gdm/gdm_base.py for the base classes and DESDEO/desdeo/api/models/gdm/gdm_aggregate.py for aggregation. Same goes for the routers. There's also method specific classes, as can be seen from DESDEO/desdeo/api/models/gdm/gnimbus.py for Group NIMBUS. The aggregation is split so that we can later on collect all possible methods and models to be used under one websocket endpoint. More on that later.

### The models and their relations

The models within .../models/gdm/gdm_aggregate.py consists of a number of response and request models. The two most important models, however, are the table models; Group and GroupIteration. Group contains the information on the group and a link to the head group iteration. GroupIteration contains the information from iterations.

```
                         +-------------+
                         |             |
 _______         ________v_______      |     ________________
| Group | +---->| GroupIteration |  +--+--->| GroupIteration |  +-----> etc.
|_______| |     |----------------|  |  |    |----------------|  |
| head ---+     | parent -----------+  |    | parent -----------+
|_______|       | child  -----------+  |    | child  -----------+
                | VotingPref     |  |  |    | OptimPref      |  |
                | VotingState    |  |  |    | OptimState     |  |
                |________________|  |  |    |________________|  |
                                    |  |                        |
                        None <------+  +-------------+----------+
```

Here we can observe how Group holds link to the head GroupIteration, which then has links to its parents, which has links to its parent and so forth.
The GroupIteration holds and stores the information on given preferences. It is essentially a dictionary with users' ids as keys and the corresponding preference as the value. These preferences are incomplete, and when all preferences are in, we start the process of optimizing/producing a solution corresponding to those preferences.

The GroupIteration also has a connection to a State. The state is used to store the results and full preferences of the iteration: for example in above GNIMBUS case, it can hold information on how the users voted for specific solutions and what solution was chosen, or in optimization case, the reference points and what came out of those preference points. The corresponding States (VotingState, OptimizationState, EndState) are defined in ../models/state.py.

As can be observed from .../models/gdm/gnimbus.py, there's a number of GNIMBUS specific classes. The most prominent of these are the Preference classes for storing the preferences when they are incomplete. There's also a number of response classes, and are used in similar manner as any other response classes with HTTP endpoints.

### The managers

When the server is started, a singleton called ManagerManager that manages GroupManagers is spawned. Its responsibilities are to create and delete these GroupManagers. If a valid connection with an authorized user connects, ManagerManager checks whether a corresponding group/method already has a GroupManager and returns it. If there is no such GroupManager, it spawns it. Upon disconnection of a user, ManagerManager checks whether a GroupManager has any remaining connections. If there are none, the singleton deletes this GroupManager.

A GroupManager handles the needs of a single group. These needs are handling connections, database accesses, message broadcasts, preference updates and optimization. Next, we'll go over relevant functions. The base for this manager can be found from .../api/routers/gdm/gdm_base.py.

```def __init__(self, group_id: int)```
Naturally, this is the constructor of the object. It checks that the group corresponding to the id exists. Then it initializes a dictionary for the users' websockets.

```async def send_message(self, message: str, websocket: WebSocket)```
Just sends single message through the specified websocket.

```async def connect(self, user_id: int, websocket: WebSocket)```
Attaches the websocket in the GroupManager's websocket dictionary. Also, if the previous iteration has any notifications that aren't sent, send notifications that the results are to be fetched.

```async def disconnect(self, user_id: int, websocket: WebSocket)```
Detaches the websocket object from the GroupManager's websocket dictionary.

```async def broadcast(self, message: str)```
Sends a message to all connected websockets.

```async def notify(self, user_ids: list[int], message: str):```
Notifies all users that are connected to the Manager. Returns a dict of who is notified and who is not.

Those would be basic handling of connections and such. However, the difference between GroupManagers come from the "optimize" function and what happens within.

```async def run_method(self, user_id: int, data: str)```
This function is quite free form. There is the GNIMBUSManager to serve as an example in this case. In this function, the data is the raw data coming from websocket. That data will later be validated when we know what we want the data to be. Checks are performed to ensure that the necessary preliminary work has been done: GNIMBUS initialization has run, the wanted group exists, etc. When that is done, the execution of the function is diverged based on what is contained in the preferences class. Specifically, which method is used, in this case "optimization" or "voting" or "end". The implementation can be found at .../api/routers/gdm/gnimbus/gnimbus_manager.py.

In these different paths, represented by the "optimization", "voting" and "ending" functions, we essentially:
*   Validate the preferences as either a ReferencePoint (e.g. ```{"aspiration_levels": {"f_1": 0.4, "f_2": 0.7, "f_3": 0.1}}```) for optimization or a solution index (int) for voting or either true or false (coming in as something that can be cast to boolean) for ending the process.
*   Update the current GroupIteration's Preference field with the newest preferences.
*   If preferences from all members of the group are in, we can move on to result production (running GNIMBUS methods or voting for a result or ending for ending)
*   After those results are produced, the results and the preferences used to obtain those results are stored into States and that State is linked to the current GroupIteration.
*   Users are notified that the results are ready for fetching using separate HTTP endpoints. The notification information (as in who is notified and who is not) is stored to the iteration.
*   A new Preference item of the opposite type as the current type is created and returned from the path-specific function to the "run_method" function.

Then a new GroupIteration is formed, with the newly created and returned Preference item contained within. Group's head iteration is updated to the newest iteration, the parent/child relations between the new and old GroupIteration are set. Now the new GroupIteration's Preference item is ready to be filled with preferences coming from the websocket.

### The websockets

The websocket endpoint is found in ../routers/gdm/gdm_aggregate.py. 

The url for the websocket is ```ws://[DOMAIN]:[PORT]/gdm/ws?token=[TOKEN]&group_id=[GROUP_ID]&method=[METHOD]```, where ```[TOKEN]``` is the token that is received from the API's ```/login``` endpoint, ```[GROUP_ID]``` is, naturally, the ID of the group the user is a member of and wants to work with and ```[METHOD]``` is the corresponding method the user wants to use, e.g. gnimbus.
If the server is hosted on a server with TSL certificates etc. the appropriate protocol is ```wss:```, similar to what is the case with ```http:``` and ```https:```.
When a user connects to this websocket, they are validated as a member of the group using ```[TOKEN]``` and ```[GROUP_ID]``` and then are connected to the Group's manager corresponding to ```[METHOD]```.

For as long as the user is connected to the websocket, they can send data over to the server. The data is validated as needed as described above (in the case of GNIMBUS). The users are also notified when optimization is done or if something goes wrong as a result of their actions.

### The routers

These are just your standard HTTP endpoints. These can be used in general to manipulate groups and such. There's also the GNIMBUS specific endpoints used for fetching results and initializing the problem and such.

### Authors note after implementing the GDMScoreBands prototype

The role of the websockets has been greatly diminished in the GDMSCOREBands implementation. Currently, the system rather utilizes HTTP endpoints to communicate with the Group Manager. Each HTTP endpoint has it's corresponding method in the group manager.

In implementing the GDMSCOREBands system, it is evident that this system can be used to many degrees. One can, if they will, rely on the websockets for transferring preferences, messages, etc. and use the manager system to handle the optimization and so forth (as is done with GNIMBUS). One can also communicate with the manager through HTTPEndpoints, and implement the manager to handle the things (as is done with GDMSCOREBands). One could most likely also utilize the manager as a simple message system, making sure that the UI will fetch the right data from the right endpoint.

In hindsight, the author of this system might have been blinded with the idea of websockets as a form of back-and-forth communication. The GNIMBUS system build on top of this works, yes, but it could have been simpler. A word forward: have the HTTP endpoints access the managers through import. Then have the endpoints utilize the manager's functionality.

However, the groups and group iterations and their interplay is useful.
