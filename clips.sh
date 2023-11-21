#!/bin/bash
# File: skript.sh
# Author: Constantin Lazari
# Date: 2023-10-31
#
# Software Notice and License
# This work (and included software, documentation such as READMEs, or other related items) 
# is being provided by the copyright holders under the following license. 
#
# By obtaining, using and/or copying this work, you (the licensee) agree that you have read, understood, 
# and will comply with the following terms and conditions.
# Permission to copy, modify, and distribute this software and its documentation, with or without modification, 
# for any purpose and without fee or royalty is hereby granted, provided that you include the following on 
# ALL copies of the software and documentation or portions thereof, including modifications:
#   1. The full text of this NOTICE in a location viewable to users of the redistributed or derivative work.
#   2. Any pre-existing intellectual property disclaimers, notices, or terms and conditions. 
#      If none exist, this Software Short Notice should be included (hypertext is preferred, text is permitted) 
#      within the body of any redistributed or derivative code.
#   3. Notice of any changes or modifications to the files, including the date changes were made. 
#      (We recommend you provide URIs to the location from which the code is derived.)
#
# THIS SOFTWARE AND DOCUMENTATION IS PROVIDED "AS IS," AND COPYRIGHT HOLDERS MAKE NO REPRESENTATIONS OR WARRANTIES, 
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO, WARRANTIES OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR 
# PURPOSE OR THAT THE USE OF THE SOFTWARE OR DOCUMENTATION WILL NOT INFRINGE ANY THIRD PARTY PATENTS, COPYRIGHTS, 
# TRADEMARKS OR OTHER RIGHTS.
# COPYRIGHT HOLDERS WILL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF 
# ANY USE OF THE SOFTWARE OR DOCUMENTATION.
# The name and trademarks of copyright holders may NOT be used in advertising or publicity pertaining to the software 
# without specific, written prior permission. 
# Title to copyright in this software and any associated documentation will at all times remain with copyright holders.
# This work is licensed under the W3C Software Notice and License.
#############################################################################################################
# Change to the Clips directory
cd /home/cola/Videos/Inbox/Clips
# Loop through the files
for file in *; do
	# Get the filename without the extension
	filename="${file%.*}"

	# Start Haruna player
	haruna "$file"

	# Convert the first screenshot to a thumbnail
	mogrify -thumbnail 960x540 "$filename-0001.jpg"
	mv "$filename-0001.jpg" thumb.jpg

	# Get the genres from the user
	genres=$(zenity --list --text "Select genres:" --column "Genres" $(cat clip_genres.txt))

	# Get the plot outline from the user
	plot=$(zenity --text-info --title "Plot Outline" --text "Enter the plot outline:")

	# Get the performing artist from the user
	artist=$(zenity --entry --title "Performing Artist" --text "Enter the performing artist:")

	# Get the album from the user
	album=$(zenity --entry --title "Album" --text "Enter the album:")

	# Get the title from the user
	title=$(zenity --entry --title "Title" --text "Enter the title:")

	# Create the NFO file
	cat << EOF > "$filename.nfo"
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<musicvideo>
  <title>$title</title>
  <userrating></userrating>
  <track>1</track>
  <album>$album</album>
  <plot>$plot</plot>
  <genre>$genres</genre>
  <director></director>
  <premiered></premiered>
  <studio></studio>
  <artist>$artist</artist>
</musicvideo>
EOF

    # Rename the clip
    mv "$file" "$filename.${file##*.}"

    # Move the associated files to the artist/title directory
    mkdir -p "/home/cola/Videos/Clips/$artist/$filename"
    mv "$filename.${file##*.}" "$filename.nfo" thumb.jpg "/home/cola/Videos/Clips/$artist/$filename"
done
