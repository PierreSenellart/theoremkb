#!/bin/sh

month=`echo $1 | perl -pe 's/\..*//'`

cp /external/theoremkb/aws-data/src*/$month/$1.gz .
mkdir $1
cd $1
mkdir in
cd in
if zcat ../../$1.gz | file -i - | grep -q text/x-tex
then
  zcat ../../$1.gz > $1.tex
else
  tar zxf ../../$1.gz
fi
cd ../..
./add_extthm.py $1/in $1/out
cd $1/out
ln -s ../../extthm.sty
cd ../..
rm $1.gz
