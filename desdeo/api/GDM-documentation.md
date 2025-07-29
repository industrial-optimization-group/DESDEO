# GROUP DECISION MAKING framework documentation
This is a documentation on how the group decision making is implemented, how it can be modified to generalize different preference information, etc.

Tool that have been used in testing:
* websocketking.com: allows creating websockets and sending data through them.

Relevant and modified files in DESDEO:
* desdeo/api/app.py: added the gdm router
* desdeo/api/models/\_\_init\_\_.py: added the gdm models
* desdeo/api/models/gdm.py: added group decision making models
* desdeo/api/routers/gdm.py: added group decision making functionality
* desdeo/api/tests/test\_models.py: testing
* desdeo/api/tests/test\_router.py: testing
* pyproject.toml: added websockets as dependency

## Notes on the implementation
To start, in the routers/gdm.py file we can see a number of endpoint for group manipulation. We can create and delete groups, add and remove users from them, initialize the group's problem (in the case of nimbus), get group info and fetch the results of the latest iteration of the group. These work like any other HTTP endpoint accross the DESDEO API. There is one non standard endpoint, and that is the websocket endpoint.

### The models
The models in models/gdm.py consist of two main table models: Group table model and GroupIteration table model. Rest of them are request- and response models. The Group model holds data on the Group: id, name, owner's id, list of group member ids and the id of the problem that the group has. It also has a reference to the latest GroupIteration. The GroupIteration model handles the data within the iterations: the preferences of that iteration, the results of that iteration, whether users have been notified, and references to the group, iteration's parent and its child.

Visually, the Group/GroupIteration relationships look like this:

                             +-------------+
                             |             |
     _______         ________v_______      |     ________________
    | Group | +---->| GroupIteration |  +--+--> | GroupIteration |  +-----> etc.
    |_______| |     |----------------|  |  |    |----------------|  |
    | head ---+     | parent -----------+  |    | parent -----------+
    |       |       | child  -----------+  |  | child  -----------+
    |_______|       |________________|  |  |    |________________|  |
                                        |  |                        |
                            None <------+  +-------------+----------+

We can observe a doubly linked list type structure here.

### ManagerManager and GroupManager
When the server is started, a singleton called ManagerManager that manages connection/preference/optimization managers is spawned. Its responsibilities are to create and delete these managers. If a valid connection, with authorized user connects, ManagerManager checks whether a corresponding group already has a group manager and returns it. If there is no such group manager, it spawns it. Upon disconnection of a user, ManagerManager checks whether a group manager has any remaining connections. If there are none, the singleton deletes this manager.

A GroupManager handles the needs of a single group. These needs are handling connections, database access, broadcasting messages, preference updates and optimization. Lets's go over its functionality function by function.

### Walkthrough
The URL of the websocket endpoint is ws://[DOMAIN]:[PORT]/gdm/ws?token=[TOKEN]&group\_id=[GROUP\_ID]. Any tool that can create websockets and send data through them can be utilized for testing. I have been using websocketking.com. It allows multiple connections, saving payloads and urls.

When a proper call to the endpoint is created, the parameters will be validated. Group's ID and the token are checked from database and using jwt token tools. If validation fails, the other end (the user) is notified of this and the websocket is closed.

If validation succeeds, a GroupManager is fetched by ManagerManager. The websocket is then attached to the GroupManager. Then data from the websocket is waited repeatedly until the user disconnects. Every time data is received, it is validated as ReferencePoint. (This, however, could be any type of preference and allows for generalization.) If validation succeeds, the GroupManager uses these preferences to update the GroupIteration in the database.

When all preferences are in, the GroupManager then begins optimization. The GroupManager synthesizes the preferences (currently, only selects one ReferencePoint from the database but allows generalization) and uses that to optimize (currently does only NIMBUS but allows generalization). The results are then written into the current iteration's database entry, and the connected users notified. A new iteration is created and the current iteration is set as its parent iteration. If a user is not connected during the optimization, they obviously are not notified. However, when they connect to the websocket endpoint for the next time, they will receive a notification that there are results to be fetched.The user can then fetch these results using separate HTTP endpoint.

An astute observer might also have realized that the system does not utilize the existing state system of the surrounding framework. This is true, but I believe it could be implemented as a method-specific parallel system to the GroupIteration system.

- Vili
