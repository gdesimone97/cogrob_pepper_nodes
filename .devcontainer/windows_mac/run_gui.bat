docker build .. -f ../Dockerfile -t cogrob
docker run -it --rm -p 33890:3389 -v ${PWD}\..\..:/workspace cogrob