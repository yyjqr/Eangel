    #sudo tar -zxvf jdk-8u351-linux-aarch64.tar.gz -C /usr/local/
    #sudo mv jdk1.8.0_351/ ./java
sudo tar -zxvf jdk-18.0.2.1_linux-aarch64_bin.tar.gz   -C /usr/local/
    #export JAVA_HOME=/usr/local/java
   export JAVA_HOME=/usr/local/jdk-18.0.2.1
#sleep 1
    export JRE_HOME=$JAVA_HOME/jre
    #sleep 1 
    export CLASSPATH=.:$JAVA_HOME/lib:$JRE_HOME/lib
    
    export PATH=$PATH:$JAVA_HOME/bin:$JRE_HOME/bin
   echo "java version"
   #java -version
