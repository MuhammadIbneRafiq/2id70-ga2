
# Summary: What I Changed and What I Learned

## What I Changed

### 1. **[pom.xml](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/pom.xml:0:0-0:0)** — Java 17 → 21
```xml
<maven.compiler.source>21</maven.compiler.source>
<maven.compiler.target>21</maven.compiler.target>
```

### 2. **[config.txt](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/config.txt:0:0-0:0)** — WSL-native Unix commands
```@c:\Users\wifi stuff\OneDrive - TU Eindhoven\2id70-ga2\GQS\config.txt:1-3
startCommand=bash ~/neo4j_start.sh THREAD_FOLDER THREAD_WEB THREAD_SERVER
stopCommand=bash ~/neo4j_stop.sh THREAD_WEB
resetCommand=bash ~/neo4j_reset.sh THREAD_FOLDER
```

### 3. **WSL Setup** — Neo4j 5.20.0 + Java 21
- Downloaded Neo4j Community 5.20.0 to `~/neo4j-template` in WSL
- Configured [neo4j.conf](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/neo4j/packaging/standalone/standalone-community/src/main/distribution/text/community/conf/neo4j.conf:0:0-0:0): disabled auth, set ports to `0.0.0.0:___PORT___1` and `0.0.0.0:___PORT___2`
- Created helper scripts: `~/neo4j_start.sh`, `~/neo4j_stop.sh`, `~/neo4j_reset.sh`
- Downloaded Java 21 (Temurin) to `~/jdk-21.0.10+7/`

### 4. **[Main.java](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/src/main/java/org/example/gqs/Main.java:0:0-0:0)** — Increased Neo4j startup timeout
Changed line 728 from `if (cnt > 20)` to `if (cnt > 60)` to give Neo4j 60 seconds to start instead of 20.

### 5. **Created 3 helper scripts in WSL**
- **[neo4j_start.sh](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/neo4j_start.sh:0:0-0:0)**: Copies template, replaces ports, starts Neo4j
- **[neo4j_stop.sh](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/neo4j_stop.sh:0:0-0:0)**: Kills by PID + port (handles zombie processes)
- **[neo4j_reset.sh](cci:7://file:///c:/Users/wifi%20stuff/OneDrive%20-%20TU%20Eindhoven/2id70-ga2/GQS/neo4j_reset.sh:0:0-0:0)**: Deletes the thread folder

---

## What I Learned

### The Core Problem
**Windows ↔ WSL2 networking**: Neo4j running in WSL2 on `127.0.0.1` isn't reachable from Windows Java processes. The fix: **run GQS entirely inside WSL** where both GQS and Neo4j share the same network.

### The Solution Architecture
```
Windows                          WSL2 (Ubuntu)
--------                         -------------
GQS JAR file  ────────────────>  Java 21 runs GQS JAR
config.txt                       ↓
                                 Spawns Neo4j instances
                                 (bolt: 20000, 20001, ...)
                                 ↓
                                 GQS connects via localhost
                                 ↓
                                 Logs bugs to Windows filesystem
```

---

## How to Run GQS for Hours (or Endlessly)

### **Command to run for K hours:**
```bash
wsl bash -c "cd '/mnt/c/Users/wifi stuff/OneDrive - TU Eindhoven/2id70-ga2/GQS' && ~/jdk-21.0.10+7/bin/java -jar target/GQS-1.0-SNAPSHOT.jar --timeout-seconds=SECONDS neo4j 2>&1 | tee gqs_run.log"
```

Replace `SECONDS` with your desired runtime:
- **4 hours**: `14400`
- **12 hours**: `43200`
- **24 hours**: `86400`
- **Endless** (1 year): `31536000`

### **Example: Run for 8 hours**
```bash
wsl bash -c "cd '/mnt/c/Users/wifi stuff/OneDrive - TU Eindhoven/2id70-ga2/GQS' && ~/jdk-21.0.10+7/bin/java -jar target/GQS-1.0-SNAPSHOT.jar --timeout-seconds=28800 neo4j 2>&1 | tee gqs_run.log"
```

The `| tee gqs_run.log` saves console output to a file while still showing it on screen.

---

## How to Change Neo4j Versions

### **Option 1: Download a different version to WSL**
```bash
# In WSL, download Neo4j 5.26.0 (or any 5.x version)
wsl bash -c "curl -L https://dist.neo4j.org/neo4j-community-5.26.0-unix.tar.gz -o ~/neo4j-5.26.0.tar.gz"

# Extract and replace the template
wsl bash -c "cd ~ && tar -xzf neo4j-5.26.0.tar.gz && rm -rf neo4j-template && mv neo4j-community-5.26.0 neo4j-template"

# Re-apply the configuration
wsl bash -c "sed -i 's/#dbms.security.auth_enabled=false/dbms.security.auth_enabled=false/' ~/neo4j-template/conf/neo4j.conf && sed -i 's|#server.bolt.listen_address=:7687|server.bolt.listen_address=0.0.0.0:___PORT___1|' ~/neo4j-template/conf/neo4j.conf && sed -i 's|#server.http.listen_address=:7474|server.http.listen_address=0.0.0.0:___PORT___2|' ~/neo4j-template/conf/neo4j.conf"

# Copy the change_port.sh script
wsl bash -c "cp '/mnt/c/Users/wifi stuff/OneDrive - TU Eindhoven/2id70-ga2/GQS/change_port.sh' ~/neo4j-template/change_port.sh && chmod +x ~/neo4j-template/change_port.sh && sed -i 's/\r//' ~/neo4j-template/change_port.sh"
```

### **Option 2: Update the driver version in pom.xml (if needed)**
If you switch to a very different Neo4j version (e.g., 4.x or 6.x), update `@c:\Users\wifi stuff\OneDrive - TU Eindhoven\2id70-ga2\GQS\pom.xml:148-149`:
```xml
<groupId>org.neo4j.driver</groupId>
<artifactId>neo4j-java-driver</artifactId>
<version>5.26.0</version>  <!-- Change this to match Neo4j version -->
```

Then rebuild:
```bash
mvn install -DskipTests -T1C
```

---

## Where Logs Are Stored

Bug logs appear in:
```
c:\Users\wifi stuff\OneDrive - TU Eindhoven\2id70-ga2\GQS\logs\6\neo4j\
```

Each file contains:
- Timestamp
- Database name and seed value
- Full Cypher query sequence that triggered the bug
- Stack trace (if applicable)

---

## Quick Reference Card

| Task | Command |
|------|---------|
| **Run for 4 hours** | `wsl bash -c "cd '/mnt/c/Users/wifi stuff/OneDrive - TU Eindhoven/2id70-ga2/GQS' && ~/jdk-21.0.10+7/bin/java -jar target/GQS-1.0-SNAPSHOT.jar --timeout-seconds=14400 neo4j"` |
| **Check logs** | `ls "c:\Users\wifi stuff\OneDrive - TU Eindhoven\2id70-ga2\GQS\logs\6\neo4j\"` |
| **Kill running test** | `Stop-Process -Name java -Force` |
| **Clean up Neo4j instances** | `wsl bash ~/neo4j_stop.sh 20000` |
| **Rebuild after code changes** | `mvn install -DskipTests -T1C` |

Everything is ready to run. Just execute the command with your desired timeout and let it find bugs.