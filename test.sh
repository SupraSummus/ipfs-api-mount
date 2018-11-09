#!/bin/sh
cat tests/test_dirs | xargs -n1 tests/test_re_add.sh
tests/test_permissions.sh
