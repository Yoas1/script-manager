#!/bin/bash

cat << "EOF"
__  __                ___   ____               _           __      
\ \/ /___  ____ _____<  /  / __ \_________    (_)__  _____/ /______
 \  / __ \/ __ `/ ___/ /  / /_/ / ___/ __ \  / / _ \/ ___/ __/ ___/
 / / /_/ / /_/ (__  ) /  / ____/ /  / /_/ / / /  __/ /__/ /_(__  ) 
/_/\____/\__,_/____/_/  /_/   /_/   \____/_/ /\___/\___/\__/____/  
                                        /___/                      
EOF

pip install -r /scripts/requirements.txt
uvicorn main:app --reload --host 0.0.0.0
