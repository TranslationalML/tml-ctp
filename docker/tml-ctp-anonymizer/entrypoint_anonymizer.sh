#!/bin/bash

# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

cd /app/DicomAnonymizerTool/build/DicomAnonymizerTool
java -jar DAT.jar "$@"
