This is a simple website with following functions
- sqlite database read / write using 
- authentification using Google OAuth 


Settings: to run the code, you need to:  
- install VirtualBox 
- install Vagrant, and run "vagrant ssh" in the directory wwhere Vatfantfile is located 
- setup OAuth service with Google, and download setting CSV. Change the nmae into "client_secretes.json" and located at the root folder of this project 
- run "database_setup.py" with Python3. This is to create database
- run "project.py" with Python3. This runs webserver on localhost
- access to localhost:5000 

Access routes: 
- Website access point -   / 
- API access point -   /catalog.json 



