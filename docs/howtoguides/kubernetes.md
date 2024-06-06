# How to host a DESDEO web application on Kubernetes

This is a how-to guide to setting up a DESDEO web application on Kubernetes. Specifically, the aim is to provide one easy way to get desdeo-webapi, desdeo-webui and a database running on [CSC Rahti](https://docs.csc.fi/cloud/rahti2/). Rahti is running Openshift OKD v4 with Kubernetes v1.28. If you are trying to host your web application somewhere else, all the steps presented here might not be directly applicable, but the process should be similar.

## Getting started on Rahti

The first thing to do, is to create a project for your web application. To be able to do that on Rahti, you will first need CSC computing project to associate it with. See the [Rahti documentation](https://docs.csc.fi/cloud/rahti2/access/) on how to create one.

The next step is to login to the [Rahti web interface](https://console-openshift-console.apps.2.rahti.csc.fi/). Once you are in, look for a `create project` button. You will likely need to be in the administrator role to see it. Input the name of the of the project, add a display name if you want one, and add a description. In Rahti the name of the project is kind of important, because it will appear as a part of all the automatically generated URLs pointing to your web application, so you will want to choose something short and to the point. In the description you will need to include the Project Number of your CSC computing project in format `csc_project:1234567`.
!!! Note
    It will take some time for the Rahti system to become aware of newly created computing projects. If you just created a new computing project and are getting an error when creating a Rahti project, just wait and it should sort itself out.

Once you have your project set up, you can start adding resources to your project.

## DESDEO webapi

To add a new resource i.e. piece of your web application, navigate to the `+Add` page. There, you want to choose `Import from Git` option. 

First, you will need to input a Github adress to the repository that contains your DESDEO webapi code, for example `https://github.com/industrial-optimization-group/desdeo-webapi`. You are unlikely to be using the main branch of the Git for your deployment, so click `Show advanced Git options` and add the name of your desired branch under `Git reference`. You probably don't need to touch any of the other advanced options.

At this point, the system should have automatically figured out that you want to host a Python application and chosen you an appropriate `Builder Image version`. But if not, you can set it up manually.

Under the **General** section, you can choose the name of your application, which does not matter much, because it will not be visible outside the administrative interface, and the `Name` of your application component, which is kind of important, because it will be part of any URL pointing to that component. For the webapi it does not matter too much what you choose, but put some thought into what you name the webui, because your users are connecting to that part and can see the name.

Under **Build** section you may want to adjust the advanced Build options, because that is the place to set up Environment variables that are present both during the build and while the application is running. This is a good way to tell your DESDEO webapi, for example, where to find the database it is supposed to connect to. At the time of writing this, neither the master branch of desdeo-webapi nor the API found in DESDEO2 offer any automatic support reading application configurations from environmental variables. Hopefully this will change in the future. 

If you want to add some python code that uses environmental variables, you can do it like this:
```python
import os

db_user = os.environ.get("POSTGRES_USER")
db_password = os.environ.get("POSTGRES_PASSWORD")
db_host = os.environ.get("POSTGRES_HOST")
db_port = os.environ.get("POSTGRES_PORT")
db_name = os.environ.get("POSTGRES_DB")
```
The above code reads five environmental variables whose names start with `POSTGRES_` and assigns them to python variables to be used later.

You can also use the environmental variables you have defined here in any of your [S2I](#source-to-image-s2i) scripts. It is possible to also define environmental variables in your S2I scripts, but because they are uploaded on Github with your code they are not suited for storing things like database usernames and passwords.

You will likely not need to touch anything under **Deploy** or **Advanced Options** for now. When you are done with your adjustments, click `Create` and the system will attempt to download your source code from the specified location, build a docker image, and finally run it.

## Source to image (S2I)

The way Rahti transforms the code on Github to a web application is by using [Source-to-Image (S2I)](https://github.com/openshift/source-to-image) toolkit. You probably don't need to be familiar with its more intricate workings, but there is a lot of documentation and examples available online if you need it. To put simply, what S2I does is it

1. bundles up your code excluding the files defined in `.s2iignore` file,

2. sets the environment variables from `.s2i/environment`,

3. starts a container and runs the `assemble` script and waits for it to finish,

4. commits the container, setting the CMD for the output image to be the `run` script and tagging the image with the name provided.

You can modify how S2I builds and runs your code by changing these scripts.

For running a python app like desdeo-webapi, it is unlikely you will need to change the `assemble` and `run` scripts. You can do most of the necessary adjustments through the [environment variables used by s2i-python-container](https://github.com/sclorg/s2i-python-container/blob/master/3.9/README.md#environment-variables). Below is an example of `.s2i/environment` file used to run one version of desdeo-webapi
```sh
UPGRADE_PIP_TO_LATEST=1
DISABLE_PYPROJECT_TOML_PROCESSING=1
APP_MODULE=app:app
GUNICORN_CMD_ARGS=--bind=0.0.0.0:8080 --workers=2 --access-logfile=-
```
The first line tells that `pip` should be upgraded to the latest version. The second line tells that `pyproject.toml` should not be processed. `APP_MODULE` denotes the app that [gunicorn](http://docs.gunicorn.org/en/latest/run.html#gunicorn) should run. `GUNICORN_CMD_ARGS` lists the other arguments given to gunicorn i.e. the server should be run for all ip addresses at port 8080, the number of workers should be 2 (the default is way too many), and the logs should go to stdout. The end result here is that the code in app:app will be run on a Gunicorn WSGI server using the given arguments.

To run [desdeo-webui](#desdeo-webui), however, you will almost certainly need to adjust the `assemble` and `run` scripts. This is because [s2i-nodejs-container](https://github.com/sclorg/s2i-nodejs-container/blob/master/18/README.md) does not include as many configuration options through environment variables. The changes required are not very complicated however. Your modified `assemble` and `run` scripts go to `.s2i/bin/` folder. Below are files used to run one version of desdeo-webui. First the `assemble` script
```sh
/usr/libexec/s2i/assemble
npm run build
exit
```
It first runs the default nodejs assemble script found at `/usr/libexec/s2i/assemble` to install all the dependencies and such, then it runs `npm run build` to build the svelte web app, finally it exits. The custom `run` script used is even simpler
```sh
node build
```
It just runs the code as a standalone node server. For this to work, `svelte.config.js` also needs to be adjusted accordingly to use the node adapter. It is unlikely look like this for most versions of desdeo-webui found on Github.
```js
import preprocess from "svelte-preprocess";
import adapter from "@sveltejs/adapter-node";
import { vitePreprocess } from "@sveltejs/kit/vite";

/** @type {import("@sveltejs/kit").Config} */
const config = {
  // See https://kit.svelte.dev/docs/integrations#preprocessors
  preprocess: [
    vitePreprocess(),
    preprocess({
      postcss: true,
    }),
  ],
  kit: {
    // See https://kit.svelte.dev/docs/adapters
    adapter: adapter(),
  },
};

export default config;
```
For more information, see the [Svelte documentation](https://kit.svelte.dev/docs/adapter-node).

## DESDEO webui

The process of adding DESDEO webui to Rahti is very similar to the one detailed above with [DESDEO webapi](#desdeo-webapi), as long as you have done all the necessary preparations [relating to S2I](#source-to-image-s2i). First you go to the `+Add` page, then you choose `Import from Git` option. You add your Github link and write the correct branch under Advanced Git options.

The system should automatically figure out you are adding a Node application. You can change the builder image version if you need a specific version of Node for example.

Under **General** you can choose your Application, which does not matter much, but you might want to use the same one as for the webapi. You can also choose the `Name` for your application, which is somewhat important, because it will be part of the address your users will use to access the web application.

Under **Build** you could add environment variables for build and runtime, but they aren't used for anything right now.

It is unlikely you will need to touch anything under **Deploy** or **Advanced Options**.

Once you click `Create` the system should download your code, build it, and run it.

## PostgreSQL database

DESDEO webapi uses a PostgreSQL to store information about users and problems. That is why you are also going to need PostgreSQL database. If you are working on Rahti you have at least two reasonably good options for getting one running. The first one is [Pukki DBaaS](https://pukki.dbaas.csc.fi/) provided by CSC and the second one is hosting one on Rahti by choosing a PostgreSQL image from the developer catalog.

If you want to use Pukki, you first need to [add the Pukki service to your computing project](https://docs.csc.fi/accounts/how-to-add-service-access-for-project/). Then login to [Pukki](https://pukki.dbaas.csc.fi/) and add a database to your project by clicking the `Launch Instance` button.  Give a name to the instance. You probably don't need to adjust Volume Size, Datastore, or Flavor settings. In **Database Access**, you need to input the web addresses the database will be accessed from. If you are hosting DESDEO on Rahti, the address should be `86.50.229.150/32`. In **Initialize Databases** you can setup an initial database and add an admin username and password. You should do that. You don't need to touch anything under **Advanced**.

If you are hosting the database on Rahti, you just select the image and then input the initial settings similarly to what you would on Pukki.

For your web application to work, webapi also needs to know how to access the database. There is no way to pass that information to the default version of desdeo-webapi. Hopefully this will change in the future. For now, you can for example modify `app.py` to read environmental variables the way shown in [DESDEO webapi](#desdeo-webapi). You can store the address and login details as a secret in Rahti and then pass them on to builds and podds through the resource configuration.

Once your webapi knows how to access the database, you will need to initialize the database to create user accounts and passwords (and possibly other things). To do this, the easiest way is to go to the Rahti web interface find a pod running your desdeo-webapi. Click the pod, and then select the **Terminal** tab. This is effectively a terminal on a virtual computer running your webapi. Here you can run, for example, `add_exp_users.py --username user --N 1` command to add one user named user1, or some other database setup script you have created.

The users added alongside their passwords will be also stored in a CSV file named `users_and_pass.csv`. The pod you have accessed is only temporary, so you'll need to make sure to save the usernames and passwords somewhere else as well. You can print them in the terminal with command `cat ./users_and_pass.csv` and then copy them from there.

## Troubleshooting

If you manage get webapi and webui running, but you are unable to get past the login page or do much else, your webui probably does not know where the webapi server is running. The address is hardcoded in `desdeo-webui/src/lib/api.ts`, so you will need to change that to point to the correct address. Hopefully, in the future this will work differently.

If you are encountering `Login attempt failed. Please check your username and password.` errors in the login screen, and you think you have the correct username and password, it is likely that webapi is not connecting to the [database](#postgresql-database) correctly or you have not initialized the database correctly.
