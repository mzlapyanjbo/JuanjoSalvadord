# cocos2d-console



## Download

```sh
$ NOT DONE YET
```

## Install

```sh
$ NOT DONE YET
```

## Vision of cocos2d-console


A command line tool that lets you create, run, publish, debug, etc… your game. It is the swiss-army knife for cocos2d.

This command line tool is in its early stages.

Examples:

```
# starts a new project called "My Game" for multi-platform

$ cocos new "My Game" -l cpp -p org.cocos2d.mygame

$ cd "My Game"

# Will deploy the project to device and run it
$ cocos run -p android


```

# Devel Info

## Internals

`cocos.py` is an script whose only responsability is to call its plugins.
`cocos.bat` will invoke `cocos.py` on windows
`cocos` will invoke `cocos.py` on Mac OS X and linux

To get a list of all the registered plugins:

```
$ cocos
```

To run the "new" plugin:

```
$ cocos new
``` 

## Adding a new plugin to the console

You have to edit `bin/cocos2d.ini`, and add the class name of your new plugin there. Let's say that you want to add a plugin that deploys the project:


```
# should be a subclass of CCPlugin
project_deploy.CCPluginDeploy
``` 

And now you have to create a file called `project_deploy.py` in the `plugins` folder.
A new, empty plugin, would look like the code shown below:

```python
import cocos

# Plugins should be a sublass of CCPlugin
class CCPluginDeploy(cocos.CCPlugin):

		# in default category
        @staticmethod
        def plugin_category():
          return ""

        @staticmethod
        def plugin_name():
          return "deploy"

        @staticmethod
        def brief_description():
            return "Deploy the project to target."                

        def run(self, argv, dependencies):
            print "plugin called!"
            print argv

```

Plugins are divided by category, depending on it's function: project, engine, ...

The plugins of `project` is in default category, it's an empty stirng `""`.

# Comands Required

Please see this [issue](https://github.com/cocos2d/cocos2d-console/issues/27)
