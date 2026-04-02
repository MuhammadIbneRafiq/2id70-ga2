# Testing Graph Databases with Synthesized Queries: Replicating GQS with different versions of Neo4j
This repository was forked from [GQS](https://github.com/Graph-Query-Synthesis/GQS) 
and used for an assignment.

The current method of testing graph databases has a problem of false detection of logic bugs, 
which can cause social costs and trust crises. The paper Testing Graph Databases with 
Synthesized Queries (Yin et al., 2025) introduces the tool Graph Query Synthesis (GQS) to 
overcome the limitation of these current methods.

# Setup
The experiment was replicated using the Windows Subsystem for Linux (WSL) environment on Visual Studio Code,
as the original experiment was conducted on a Linux workstation.

This setup includes instructions from the repositories [GQS](https://github.com/Graph-Query-Synthesis/GQS)
and [Neo4j](https://github.com/neo4j/neo4j/tree/5.20).

We forked the repository [GQS](https://github.com/Graph-Query-Synthesis/GQS) and
added it as a submodule to this repository.

## Compile GQS
The following dependencies are needed:
```
Maven 3.9.6
Java-JDK 21.0
```
Download the needed version of Maven [here](https://www.npackd.org/p/org.apache.Maven/3.9.6).

Paste the extracted `Maven` source code folder in the `C:\Program Files\` folder. 

Add the file path `C:\Program Files\apache-maven-3.9.6\bin` as a system
environment variable.

Run the following command to compile the source code:
```
mvn install -DskipTests -T1C
```

## Install Neo4j Source Code
Download the `Neo4j 5.20` [(link)](https://github.com/neo4j/neo4j/tree/5.20) 
and `Neo4j 4.4` [(link)](https://github.com/neo4j/neo4j/tree/4.4) source codes.

For each download, perform the following steps:

Paste the extracted source code as a folder named `neo4j-<version>` inside `GQS/`.

Move the file `change_path.sh` from the folder `GQS/` to `GQS/neo4j-<version>/` folder.

Create a file `neo4j.conf` in a new folder `GQS/neo4j-<version>/conf/` containing the following:
```
server.bolt.listen_address=127.0.0.1:___PORT___1
server.http.listen_address=127.0.0.1:___PORT___2
```

Run the following commands to build Neo4j:
```
cd neo4j-<version>
mvn clean install -DskipTests -T1C
```

Extract the built application by running the following command:
```
tar -xzf packaging/standalone/target/neo4j-community-<version>-SNAPSHOT-unix.tar.gz
```

Move the extracted folder `neo4j-community-<version>-SNAPSHOT` to `GQS/`
and rename folder to `neo4j`.

Ensure that the port `20000` is not occupied by any other processes.

Initiate the testing process. Each process was run for 24 hours.
```
cd GQS
java -jar target/GQS-1.0-SNAPSHOT.jar --timeout-seconds 86400 neo4j
```

The result are logged in the folder `logs`.

## Using Windows Instead of Linux
In Visual Studio Code, the Windows Subsystem for Linux (WSL) can be used as a
virtual environment. The instructions to install this extension
can be found [here](https://code.visualstudio.com/docs/remote/wsl).

## Changes to GQS folder
We made the following changes in the foler `GQS`:
### 1. **pom.xml** — Java 17 → 21
```xml
<maven.compiler.source>21</maven.compiler.source>
<maven.compiler.target>21</maven.compiler.target>
```

### 2. **config.txt** — WSL-native Unix commands
```
startCommand=bash ~/neo4j_start.sh THREAD_FOLDER THREAD_WEB THREAD_SERVER
stopCommand=bash ~/neo4j_stop.sh THREAD_WEB
resetCommand=bash ~/neo4j_reset.sh THREAD_FOLDER
```

### 3. **Created 3 helper scripts in WSL**
- **neo4j_start.sh**: Copies template, replaces ports, starts Neo4j
- **neo4j_stop.sh**: Kills by PID + port (handles zombie processes)
- **neo4j_reset.sh**: Deletes the thread folder

# Authors
2ID70 Group 7

# References

<div id="refs" class="references csl-bib-body hanging-indent">
<div id="ref-xie2018" class="csl-entry">

Yin, Z., Liu, S., & Basin, D. (2025). Testing Graph Databases with Synthesized Queries. 
Proceedings of the ACM on Management of Data, 3(4), 1–26. <https://doi.org/10.1145/3749186>

</div>
</div>