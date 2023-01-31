CONFIG_PATH=/data/options.json

apks=$(jq --raw-output ".apks" $CONFIG_PATH)
packages=$(jq --raw-output ".packages" $CONFIG_PATH)
path=$(jq --raw-output ".path" $CONFIG_PATH)


IFS=','
# install system packages
for apk in ${apks}
do
    echo 'RUN apk add '${apk//[[:blank:]]/}
    apk add ${apk//[[:blank:]]/}
done

# install python packages
for package in ${packages}
do
    echo 'RUN pip3 install '${package//[[:blank:]]/}
    pip3 install ${package//[[:blank:]]/}
done

# run python scripts
IFS=$' \t\n'
cd /config/${path}
filenames=$(ls *.py)
for file in ${filenames};do
    echo 'RUN python3 '${file}
    python3 ${file} & 
done

while true
do
    sleep 3600
done