# Testing Graph Databases with Synthesized Queries: Replicating GQS with previously unknown and newly found logic bugs using Neo4j
In this assignment, we...

[//]: # (The paper was replicated using... WSL... Java...)

[//]: # (cite paper as well)

## Previously Unknown (Logic) Bugs From Neo4j
| Bug Numer  | Type  | Issue                                            |
| ---------  | ----- | ------------------------------------------------ |
| #1       | Logic | https://github.com/neo4j/neo4j/issues/13359      |
| #2       | Logic | https://github.com/neo4j/neo4j/issues/13489      |
| #3         | Other | https://github.com/neo4j/neo4j/issues/13457      |
| #4         | Other | https://github.com/neo4j/neo4j/issues/13469      |
| #5           | Other | https://github.com/neo4j/neo4j/issues/13473      |

## Newly Found (Logic) Bugs
| Bug Numer  | Type  | Issue                                            |
| ---------  | ----- | ------------------------------------------------ |
| #1       | Logic |     |

[//]: # (table with bugs we are replicating)

[//]: # (add soemthing about our metamorphic tester)

# Setup
This setup includes instructions from the repositories [GQS](https://github.com/Graph-Query-Synthesis/GQS)
and [Neo4j 5.20](https://github.com/neo4j/neo4j/tree/5.20).

Clone the repository [GQS](https://github.com/Graph-Query-Synthesis/GQS).

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
Download the `Neo4j 5.20` source code [here](https://github.com/neo4j/neo4j/tree/5.20).

Paste the extracted source code as a folder names `neo4j` inside `GQS/`.

Move the file `change_path.sh` from the folder `GQS/` to `GQS/neo4j/` folder.

Create a file `neo4j.conf` in a new folder `GQS/neo4j/conf/` containing the following:
```
server.bolt.listen_address=127.0.0.1:___PORT___1
server.http.listen_address=127.0.0.1:___PORT___2
```

Add a text file `config.txt` in `GQS/` containing the following:
```
startCommand=aa=$PWD; mkdir -p ~/neo4j/THREAD_FOLDER; cd ~/neo4j/THREAD_FOLDER; cp -r $aa/neo4j ~/neo4j/THREAD_FOLDER; mkdir -p ./logs/neo4j; cd neo4j; ./change_port.sh conf/neo4j.conf THREAD_WEB THREAD_SERVER; ./bin/neo4j-admin server console 2>&1 &
stopCommand=kill -9 `netstat -tulnp | grep :THREAD_WEB | awk '{print $7}' | cut -d'/' -f1`
resetCommand=rm -rf ~/neo4j/THREAD_FOLDER
```

Ensure that the port `20000` is not occupied by any other processes.

Run the following commands to build Neo4j:
```
cd neo4j
mvn clean install -DskipTests -T1C
```

Extract the built application by running the following command:
```
tar -xzf packaging/standalone/target/neo4j-community-5.20.0-SNAPSHOT-unix.tar.gz
```

Go to the directory `packaging/standalone/target` using `cd` to extract
`packaging/standalone/target/neo4j-community-5.20.0-SNAPSHOT-unix.tar.gz`

## Using Windows Instead of Linux
In VS Code, the Windows Subsystem for Linux (WSL) can be used as a
virtual environment. The instructions to install this extension
can be found [here](https://code.visualstudio.com/docs/remote/wsl).

# Authors
2ID70 Group 7



