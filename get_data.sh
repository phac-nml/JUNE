#!/bin/sh

#https://drive.google.com/open?id=1v82HGQsiN-2763rf6T-sNx22Vpq_GLfB
fileId=1v82HGQsiN-2763rf6T-sNx22Vpq_GLfB
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName} 

unzip data.zip
rm data.zip
rm cookie
