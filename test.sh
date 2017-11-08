#!/bin/sh
cat test/test_dirs | xargs -n1 test/test_re_add.sh
test/test_permissions.sh
