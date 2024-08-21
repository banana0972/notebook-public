## Why
Onenote, except Microsoft somehow cant make a proper document editor so I had to make a worse version myself.
What
## What
* A notebook that stores all the documents in google drive
* Integrates with the google drive api as a backend storage system.
* Embeds a google docs editor side by side, similar to onenote
* All folders/files made are mirrored to a google drive folder
## How
* Flask with jinjax for fronend
* Sqlite for user and file tracking database
* Google apis for auth and drive storage 
* Pydantic allowed for easier parsing and validation of request arguments
## Challenges
* First time using oauth, had to read up on what it does and how to properly do authorization
* Sleep deprivation
* Messing up operations on the closure table that lead to the mirrored folder structure being incorrect
## Accomplishments
* Oauth works
* Getting banned from render.com somehow
## Learning points
* Type hinting in python is surprisingly hard due to the circular imports of types
## What's next
* The basic apis and wrappers over files are ready, it would be possible to implement the similar features in onenote such as teacher folders, collaboration spaces, individual files
