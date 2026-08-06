How to run:
* Follow the setup instructions of w3schools for MongoDB
* Follow the tutorial to connect your MongoDB Atlas cluster to your VSCode
* Ensure mongosh is installed in your system and MongoDB extension is in VSCode
    * Check mongosh by running ```mongosh --version```
* Run ```pip install -r requirements.txt```
* Create a .env file in the Data Warehousing folder specifically. Content:
```
ATLAS_URI = {Your Atlas URI credential}
ATLAS_DATABASE = juanmart_datalake
```
* On a terminal with mongosh installed, either VSCode or OS Terminal just make sure to cd to the Data Warehousing folder, run:
```mongosh "mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/juanmart_landing_zone" 01_datalake_setup.mongodb.js```
    * Replace with your URI
* In VSCode terminal, cd to Data Warehousing and run ```python -c "from juanmart_landing.db import health_check; print(health_check())"```
    * If you see something like (True, {'status': 'healthy', 'latency_ms': 1104.9, 'database': 'juanmart_landing_zone', 'host': None}), alles gut