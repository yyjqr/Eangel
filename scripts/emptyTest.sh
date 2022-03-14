#!/bin/bash
# author: (http://www.linuxidc.com/)
# des: delete empty directories recursive
deleteempty() {
  #慎用，注意传入的路径目录之类！！！！！
  #find ${1:-.} -mindepth 1 -maxdepth 1 -type d | while read -r dir
  find $1 -mindepth 1 -maxdepth 1 -type d | while read -r dir
  do
    if [[ -z "$(find "$dir" -mindepth 1 -type f)" ]] >/dev/null
    then
      echo "$dir"
      rm -rf ${dir} 2>&- && echo "Empty, Deleted!" || echo "Delete error"
    fi
    if [ -d ${dir} ]
    then
      deleteempty "$dir"
    fi
  done
}
deleteempty $1
