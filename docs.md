Processing an image
Processing images with imgproxy is really easy: just send an HTTP GET request to imgproxy and imgproxy will respond with a processed image.

tip
imgproxy responds with an image file and uses an image/\* Content-Type header, so you can put imgproxy's URLs right into src attributes of your <img/> HTML tags or into url() CSS values

The request URL path should consist of a signature, processing options, a source URL, and optionally an extension, like this:

http://imgproxy.example.com/%signature/%processing_options/plain/%source_url@%extension
http://imgproxy.example.com/%signature/%processing_options/%encoded_source_url.%extension
http://imgproxy.example.com/%signature/%processing_options/enc/%encrypted_source_url.%extension

Check out the example at the end of this guide.

Signature
warning
The signature part should always be present in a URL. If the signature check is disabled (no key/salt pairs are provided), the signature part may contain anything (for example, unsafe or \_).

A signature protects your URL from being altered by an attacker. It is highly recommended to sign imgproxy URLs when imgproxy is being used in production.

Once you set up your URL signature, check out the Signing the URL guide to find out how to sign your URLs. Otherwise, since the signature still needs to be present, feel free to use any string here.

Processing options
Processing options should be specified as URL parts divided by slashes (/). A processing option has the following format:

%option_name:%argument1:%argument2:...:%argumentN

tip
You can redefine the arguments separator with the the IMGPROXY_ARGUMENTS_SEPARATOR config. For example, if you set IMGPROXY_ARGUMENTS_SEPARATOR=",", processing options will have the following format:

%option_name,%argument1,%argument2,...,%argumentN

info
The list of processing options does not define imgproxy's processing pipeline. Instead, imgproxy already comes with a specific, built-in image processing pipeline for maximum performance. Read more about this in the About processing pipeline guide.

imgproxy supports the following processing options:

Resize
resize:%resizing_type:%width:%height:%enlarge:%extend
rs:%resizing_type:%width:%height:%enlarge:%extend

This is a meta-option that defines the resizing type, width, height, enlarge, and extend. All arguments are optional and can be omitted to use their default values.

Size
size:%width:%height:%enlarge:%extend
s:%width:%height:%enlarge:%extend

This is a meta-option that defines the width, height, enlarge, and extend. All arguments are optional and can be omitted to use their default values.

Resizing type
resizing_type:%resizing_type
rt:%resizing_type

Defines how imgproxy will resize the source image. Supported resizing types are:

fit: resizes the image while keeping aspect ratio to fit a given size.
fill: resizes the image while keeping aspect ratio to fill a given size and crops projecting parts.
fill-down: the same as fill, but if the resized image is smaller than the requested size, imgproxy will crop the result to keep the requested aspect ratio.
force: resizes the image without keeping the aspect ratio.
auto: if both source and resulting dimensions have the same orientation (portrait or landscape), imgproxy will use fill. Otherwise, it will use fit.
Default: fit

Resizing algorithm Pro
resizing_algorithm:%algorithm
ra:%algorithm

Defines the algorithm that imgproxy will use for resizing. Supported algorithms are nearest, linear, cubic, lanczos2, and lanczos3.

Default: lanczos3

Width
width:%width
w:%width

Defines the width of the resulting image. When set to 0, imgproxy will calculate width using the defined height and source aspect ratio. When set to 0 and resizing type is force, imgproxy will keep the original width.

Default: 0

Height
height:%height
h:%height

Defines the height of the resulting image. When set to 0, imgproxy will calculate resulting height using the defined width and source aspect ratio. When set to 0 and resizing type is force, imgproxy will keep the original height.

Default: 0

Min width
min-width:%width
mw:%width

Defines the minimum width of the resulting image.

warning
When both width and min-width are set, the final image will be cropped according to width, so use this combination with care.

Default: 0

Min height
min-height:%height
mh:%height

Defines the minimum height of the resulting image.

warning
When both height and min-height are set, the final image will be cropped according to height, so use this combination with care.

Default: 0

Zoom
zoom:%zoom_x_y
z:%zoom_x_y

zoom:%zoom_x:%zoom_y
z:%zoom_x:%zoom_y

When set, imgproxy will multiply the image dimensions according to these factors. The values must be greater than 0.

Can be combined with width and height options. In this case, imgproxy calculates scale factors for the provided size and then multiplies it with the provided zoom factors.

info
Unlike the dpr option, the zoom option doesn't affect gravities offsets, watermark offsets, and paddings.

Default: 1

Dpr
dpr:%dpr

When set, imgproxy will multiply the image dimensions according to this factor for HiDPI (Retina) devices. The value must be greater than 0.

info
The dpr option affects gravities offsets, watermark offsets, and paddings to make the resulting image structures with and without the dpr option applied match.

Default: 1

Enlarge
enlarge:%enlarge
el:%enlarge

When set to 1, t or true, imgproxy will enlarge the image if it is smaller than the given size.

Default: false

Extend
extend:%extend:%gravity
ex:%extend:%gravity

When extend is set to 1, t or true, imgproxy will extend the image if it is smaller than the given size.
gravity (optional) accepts the same values as the gravity option, except sm, obj, and objw. When gravity is not set, imgproxy will use ce gravity without offsets.
Default: false:ce:0:0

Extend aspect ratio
extend_aspect_ratio:%extend:%gravity
extend_ar:%extend:%gravity
exar:%extend:%gravity

When extend is set to 1, t or true, imgproxy will extend the image to the requested aspect ratio.
gravity (optional) accepts the same values as the gravity option, except sm, obj, and objw. When gravity is not set, imgproxy will use ce gravity without offsets.
Default: false:ce:0:0

Gravity
gravity:%type:%x_offset:%y_offset
g:%type:%x_offset:%y_offset

When imgproxy needs to cut some parts of the image, it is guided by the gravity option.

type - specifies the gravity type. Available values:
no: north (top edge)
so: south (bottom edge)
ea: east (right edge)
we: west (left edge)
noea: north-east (top-right corner)
nowe: north-west (top-left corner)
soea: south-east (bottom-right corner)
sowe: south-west (bottom-left corner)
ce: center
x_offset, y_offset - (optional) specifies the gravity offset along the X and Y axes:
When x_offset or y_offset is greater than or equal to 1, imgproxy treats it as an absolute value.
When x_offset or y_offset is less than 1, imgproxy treats it as a relative value.
Default: ce:0:0

Special gravities:

gravity:sm: smart gravity. libvips detects the most "interesting" section of the image and considers it as the center of the resulting image. Offsets are not applicable here.
gravity:obj:%class_name1:%class_name2:...:%class_nameN: Pro object-oriented gravity. imgproxy detects objects of provided classes on the image and calculates the resulting image center using their positions. If class names are omited, imgproxy will use all the detected objects. Also, you can use the all pseudo-class to use all the detected objects.
gravity:objw:%class_name1:%class_weight1:%class_name2:%class_weight2:...:%class_nameN:%class_weightN: Pro object-oriented gravity with weights. The same as gravity:obj but with custom weights for each class. You can use the all pseudo-class to set the weight for all the detected objects. For example, gravity:objw:all:2:face:3 will set the weight of all the detected objects to 2 and the weight of the detected faces to 3. The default weight is 1.
gravity:fp:%x:%y: the gravity focus point. x and y are floating point numbers between 0 and 1 that define the coordinates of the center of the resulting image. Treat 0 and 1 as right/left for x and top/bottom for y.
Objcts position Pro
objects_position:%type:%x_offset:%y_offset
obj_pos:%type:%x_offset:%y_offset
op:%type:%x_offset:%y_offset

When imgproxy needs to cut some parts of the image, and the obj/objw gravity is used, the objects_position option allows you to adjust the position of the detected objects on the resulting image.

type - specifies the position type. Available values:
no: north (top edge)
so: south (bottom edge)
ea: east (right edge)
we: west (left edge)
noea: north-east (top-right corner)
nowe: north-west (top-left corner)
soea: south-east (bottom-right corner)
sowe: south-west (bottom-left corner)
ce: center
x_offset, y_offset - (optional) specifies the position offset along the X and Y axes.
Default: ce:0:0

Special positions:

objects_position:fp:%x:%y: the focus point position. x and y are floating point numbers between 0 and 1 that define the coordinates of the center of the objects' area in the resulting image. Treat 0 and 1 as right/left for x and top/bottom for y.
objects_position:prop: the proportional position. imgproxy will try to set object offsets in the resulting image proportional to their offsets in the original image. This position type allows the picture scene to be maintained after cropping.
Crop
crop:%width:%height:%gravity
c:%width:%height:%gravity

Defines an area of the image to be processed (crop before resize).

width and height define the size of the area:
When width or height is greater than or equal to 1, imgproxy treats it as an absolute value.
When width or height is less than 1, imgproxy treats it as a relative value.
When width or height is set to 0, imgproxy will use the full width/height of the source image.
gravity (optional) accepts the same values as the gravity option. When gravity is not set, imgproxy will use the value of the gravity option.
Crop aspect ratio Pro
crop_aspect_ratio:%aspect_ratio:%enlarge
crop_ar:%aspect_ratio:%enlarge
car:%aspect_ratio:%enlarge

Corrects the aspect ratio of the crop area defined with the crop processing option.

aspect_ratio - the aspect ratio that the crop area should match. When set to 0, imgproxy doesn't correct the crop area aspect ratio.
enlarge - when set to 1, t, or true, imgproxy will enlarge the crop area when needed instead of reducing it. If any dimension of the enlarged crop area exceeds the image size, imgproxy will reduce the crop area to fit the image, maintaining the requested aspect ratio.
info
This option only corrects the crop area size but doesn't correct the crop gravity. This means that if you use the following options – crop:100:200:nowe:300:400/crop_ar:1.1 – imgproxy will crop the 300x400x200x200 area. If you want imgproxy to maintain the crop area center, use the fp gravity instead.

Trim
trim:%threshold:%color:%equal_hor:%equal_ver
t:%threshold:%color:%equal_hor:%equal_ver

Removes surrounding background.

threshold - color similarity tolerance.
color - (optional) a hex-coded value of the color that needs to be cut off.
equal_hor - (optional) set to 1, t or true, imgproxy will cut only equal parts from left and right sides. That means that if 10px of background can be cut off from the left and 5px from the right, then 5px will be cut off from both sides. For example, this can be useful if objects on your images are centered but have non-symmetrical shadow.
equal_ver - (optional) acts like equal_hor but for top/bottom sides.
warning
Trimming requires an image to be fully loaded into memory. This disables scale-on-load and significantly increases memory usage and processing time. Use it carefully with large images.

info
If you know background color of your images then setting it explicitly via color will also save some resources because imgproxy won't need to automatically detect it.

info
Use a color value of FF00FF for trimming transparent backgrounds as imgproxy uses magenta as a transparency key.

info
The trimming of animated images is not supported.

Padding
padding:%top:%right:%bottom:%left
pd:%top:%right:%bottom:%left

Defines padding size using CSS-style syntax. All arguments are optional but at least one dimension must be set. Padded space is filled according to the background option.

top - top padding (and for all other sides if they haven't been explicitly set)
right - right padding (and left if it hasn't been explicitly set)
bottom - bottom padding
left - left padding
info
Padding is applied after all image transformations (except watermarking) and enlarges the generated image. This means that if your resize dimensions were 100x200px and you applied the padding:10 option, then you will end up with an image with dimensions of 120x220px.

info
Padding follows the dpr option so it will also be scaled if you've set it.

Auto rotate
auto_rotate:%auto_rotate
ar:%auto_rotate

When set to 1, t or true, imgproxy will automatically rotate images based on the EXIF Orientation parameter (if available in the image meta data). The orientation tag will be removed from the image in all cases. Normally this is controlled by the IMGPROXY_AUTO_ROTATE configuration but this processing option allows the configuration to be set for each request.

Rotate
rotate:%angle
rot:%angle

Rotates the image on the specified angle. The orientation from the image metadata is applied before the rotation unless autorotation is disabled.

info
Only 0, 90, 180, 270, etc., degree angles are supported.

Default: 0

Background
background:%R:%G:%B
bg:%R:%G:%B

background:%hex_color
bg:%hex_color

When set, imgproxy will fill the resulting image background with the specified color. R, G, and B are the red, green and blue channel values of the background color (0-255). hex_color is a hex-coded value of the color. Useful when you convert an image with alpha-channel to JPEG.

With no arguments provided, disables any background manipulations.

Default: disabled

Background alpha Pro
background_alpha:%alpha
bga:%alpha

Adds an alpha channel to background. The value of alpha is a positive floating point number between 0 and 1.

Default: 1

Adjust Pro
adjust:%brightness:%contrast:%saturation
a:%brightness:%contrast:%saturation

This is a meta-option that defines the brightness, contrast, and saturation. All arguments are optional and can be omitted to use their default values.

Brightness Pro
brightness:%brightness
br:%brightness

When set, imgproxy will adjust brightness of the resulting image. brightness is an integer number ranging from -255 to 255.

Default: 0

Contrast Pro
contrast:%contrast
co:%contrast

When set, imgproxy will adjust the contrast of the resulting image. contrast is a positive floating point number, where a value of 1 leaves the contrast unchanged.

Default: 1

Saturation Pro
saturation:%saturation
sa:%saturation

When set, imgproxy will adjust saturation of the resulting image. saturation is a positive floating-point number, where a value of 1 leaves the saturation unchanged.

Default: 1

Monochrome Pro
monochrome:%intensity:%color
mc:%intensity:%color

When intensity is greater than zero, imgproxy will convert the resulting image to monochrome.

intensity - a positive floating-point number between 0 and 1 that defines the intensity of the monochrome effect.
color - (optional) a hex-coded value of the color that will be used as a base for the monochrome palette.
Default: 0:b3b3b3

Duotone Pro
duotone:%intensity:%color1:%color2
dt:%intensity:%color1:%color2

When intensity is greater than zero, imgproxy will convert the resulting image to duotone.

intensity - a positive floating-point number between 0 and 1 that defines the intensity of the duotone effect.
color1, color2 - (optional) hex-coded values of the colors that will be used as a base for the duotone palette. color1 is the color for the dark areas, color2 is the color for the light areas.
Default: 0:000000:ffffff

Blur
blur:%sigma
bl:%sigma

When set, imgproxy will apply a gaussian blur filter to the resulting image. The value of sigma defines the size of the mask imgproxy will use.

Default: disabled

Sharpen
sharpen:%sigma
sh:%sigma

When set, imgproxy will apply the sharpen filter to the resulting image. The value of sigma defines the size of the mask imgproxy will use.

As an approximate guideline, use 0.5 sigma for 4 pixels/mm (display resolution), 1.0 for 12 pixels/mm and 1.5 for 16 pixels/mm (300 dpi == 12 pixels/mm).

Default: disabled

Pixelate
pixelate:%size
pix:%size

When set, imgproxy will apply the pixelate filter to the resulting image. The value of size defines individual pixel size.

Default: disabled

Unsharp masking Pro
unsharp_masking:%mode:%weight:%divider
ush:%mode:%weight:%divider

Allows redefining unsharp masking options. All arguments have the same meaning as Unsharp masking configs. All arguments are optional and can be omitted.

Blur detections Pro
blur_detections:%sigma:%class_name1:%class_name2:...:%class_nameN
bd:%sigma:%class_name1:%class_name2:...:%class_nameN

imgproxy detects objects of the provided classes and blurs them. If class names are omitted, imgproxy blurs all the detected objects.

The value of sigma defines the size of the mask imgproxy will use.

Draw detections Pro
draw_detections:%draw:%class_name1:%class_name2:...:%class_nameN
dd:%draw:%class_name1:%class_name2:...:%class_nameN

When draw is set to 1, t or true, imgproxy detects objects of the provided classes and draws their bounding boxes, classes, and confidences. If class names are omitted, imgproxy draws the bounding boxes of all the detected objects.

Colorize Pro
colorize:%opacity:%color:%keep_alpha
col:%opacity:%color:%keep_alpha

Places a color overlay on the processed image.

opacity: specifies the overlay opacity. When set to 0, overlay is not applied.
color: (optional) a hex-coded value of the overlay color. Default: 000 (black).
keep_alpha: (optional) when set to 1, t or true, imgproxy will keep the alpha channel of the original image. Default: false
Gradient Pro
gradient:%opacity:%color:%direction:%start:%stop
gr:%opacity:%color:%direction:%start:%stop

Places a gradient on the processed image. The placed gradient transitions from transparency to the specified color.

opacity: specifies gradient opacity. When set to 0, gradient is not applied.
color: (optional) a hex-coded value of the gradient color. Default: 000 (black).
direction: (optional) specifies the direction of the gradient. The direction can be specified in two ways:
An angle in degrees (clockwise). For example, 0 will create a gradient from top to down (the top side is transparrent, the bottom side is opaque), and 90 will create a gradient from right to left (the right side is transparrent, the left side is opaque).
A string value. Available values:
down: (default) the top side of the gradient is transparrent, the bottom side is opaque
up: the bottom side of the gradient is transparrent, the top side is opaque
right: the left side of the gradient is transparrent, the right side is opaque
left: the right side of the gradient is transparrent, the left side is opaque
start, stop: floating point numbers that define relative positions of where the gradient starts and where it ends. Default values are 0.0 and 1.0 respectively.
Watermark
watermark:%opacity:%position:%x_offset:%y_offset:%scale
wm:%opacity:%position:%x_offset:%y_offset:%scale

Places a watermark on the processed image.

opacity: watermark opacity modifier. Final opacity is calculated like base_opacity \* opacity.
position: (optional) specifies the position of the watermark. Available values:
ce: (default) center
no: north (top edge)
so: south (bottom edge)
ea: east (right edge)
we: west (left edge)
noea: north-east (top-right corner)
nowe: north-west (top-left corner)
soea: south-east (bottom-right corner)
sowe: south-west (bottom-left corner)
re: repeat and tile the watermark to fill the entire image
ch: Pro same as re but watermarks are placed in a chessboard order
x_offset, y_offset - (optional) specify watermark offset by X and Y axes:
When x_offset or y_offset is greater than or equal to 1 or less than or equal to -1, imgproxy treats it as an absolute value.
When x_offset or y_offset is less than 1 and greater than -1, imgproxy treats it as a relative value.
When using re or ch position, these values define the spacing between the tiles.
scale: (optional) a floating-point number that defines the watermark size relative to the resultant image size. When set to 0 or when omitted, the watermark size won't be changed.
Default: disabled

Watermark URL Pro
watermark_url:%url
wmu:%url

When set, imgproxy will use the image from the specified URL as a watermark. url is the URL-safe Base64-encoded URL of the custom watermark.

Default: blank

Watermark text Pro
watermark_text:%text
wmt:%text

When set, imgproxy will generate an image from the provided text and use it as a watermark. text is the URL-safe Base64-encoded text of the custom watermark.

By default, the text color is black and the font is sans 16. You can use Pango markup in the text value to change the style.

If you want to use a custom font, you need to put it in /usr/share/fonts inside a container.

Default: blank

Watermark size Pro
watermark_size:%width:%height
wms:%width:%height

Defines the desired width and height of the watermark. imgproxy always uses fit resizing type when resizing watermarks and enlarges them when needed.

When %width is set to 0, imgproxy will calculate the width using the defined height and watermark's aspect ratio.

When %height is set to 0, imgproxy will calculate the height using the defined width and watermark's aspect ratio.

info
This processing option takes effect only when the scale argument of the watermark option is set to zero.

Default: 0:0

Watermark rotate Pro
watermark_rotate:%angle
wm_rot:%angle
wmr:%angle

Rotates the watermark on the specified angle (clockwise). The orientation from the image metadata is applied before the rotation.

Default: 0

Watermark shadow Pro
watermark_shadow:%sigma
wmsh:%sigma

When set, imgproxy will add a shadow to the watermark. The value of sigma defines the size of the mask imgproxy will use to blur the shadow.

Default: disabled

Style Pro
style:%style
st:%style

When set, imgproxy will prepend a <style> node with the provided content to the <svg> node of a source SVG image. %style is URL-safe Base64-encoded CSS-styles.

Default: blank

Strip metadata
strip_metadata:%strip_metadata
sm:%strip_metadata

When set to 1, t or true, imgproxy will strip the output images' metadata (EXIF, IPTC, etc.). This is normally controlled by the IMGPROXY_STRIP_METADATA configuration but this processing option allows the configuration to be set for each request.

Keep copyright
keep_copyright:%keep_copyright
kcr:%keep_copyright

When set to 1, t or true, imgproxy will not remove copyright info while stripping metadata. This is normally controlled by the IMGPROXY_KEEP_COPYRIGHT configuration but this processing option allows the configuration to be set for each request.

DPI Pro
dpi:%dpi

When set, imgproxy will replace the image's DPI metadata with the provided value. When set to 0, imgproxy won't change the image's DPI or will reset it to the default value if the image's metadata should be stripped.

info
This processing option takes effect whether imgproxy should strip the image's metadata or not.

Default: 0

Strip color profile
strip_color_profile:%strip_color_profile
scp:%strip_color_profile

When set to 1, t or true, imgproxy will transform the embedded color profile (ICC) to sRGB and remove it from the image. Otherwise, imgproxy will try to keep it as is. This is normally controlled by the IMGPROXY_STRIP_COLOR_PROFILE configuration but this processing option allows the configuration to be set for each request.

Enforce thumbnail
enforce_thumbnail:%enforce_thumbnail
eth:%enforce_thumbnail

When set to 1, t or true and the source image has an embedded thumbnail, imgproxy will always use the embedded thumbnail instead of the main image. Currently, only thumbnails embedded in heic and avif are supported. This is normally controlled by the IMGPROXY_ENFORCE_THUMBNAIL configuration but this processing option allows the configuration to be set for each request.

Quality
quality:%quality
q:%quality

Redefines quality of the resulting image, as a percentage. When set to 0, quality is assumed based on IMGPROXY_QUALITY and format_quality.

Default: 0.

Format quality
format_quality:%format1:%quality1:%format2:%quality2:...:%formatN:%qualityN
fq:%format1:%quality1:%format2:%quality2:...:%formatN:%qualityN

Adds or redefines IMGPROXY_FORMAT_QUALITY values.

Autoquality Pro
autoquality:%method:%target:%min_quality:%max_quality:%allowed_error
aq:%method:%target:%min_quality:%max_quality:%allowed_error

Redefines autoquality settings. All arguments have the same meaning as Autoquality configs. All arguments are optional and can be omitted.

warning
Autoquality requires the image to be saved several times. Use it only when you prefer the resulting size and quality over the speed.

Max bytes
max_bytes:%bytes
mb:%bytes

When set, imgproxy automatically degrades the quality of the image until the image size is under the specified amount of bytes.

info
Applicable only to jpg, webp, heic, and tiff.

warning
When max_bytes is set, imgproxy saves image multiple times to achieve the specified image size.

Default: 0

JPEG options Pro
jpeg_options:%progressive:%no_subsample:%trellis_quant:%overshoot_deringing:%optimize_scans:%quant_table
jpgo:%progressive:%no_subsample:%trellis_quant:%overshoot_deringing:%optimize_scans:%quant_table

Allows redefining JPEG saving options. All arguments have the same meaning as the Advanced JPEG compression configs. All arguments are optional and can be omitted.

PNG options Pro
png_options:%interlaced:%quantize:%quantization_colors
pngo:%interlaced:%quantize:%quantization_colors

Allows redefining PNG saving options. All arguments have the same meaning as with the Advanced PNG compression configs. All arguments are optional and can be omitted.

WebP options Pro
webp_options:%compression:%smart_subsample:%preset
webpo:%compression:%smart_subsample:%preset

Allows redefining WebP saving options. All arguments have the same meaning as with the Advanced WebP compression configs. All arguments are optional and can be omitted.

Format
format:%extension
f:%extension
ext:%extension

Specifies the resulting image format. Alias for the extension part of the URL.

Default: jpg

Page Pro
page:%page
pg:%page

When a source image supports pagination (PDF, TIFF) or animation (GIF, WebP), this option allows specifying the page to use. Page numeration starts from zero.

info
If both the source and the resulting image formats supoprt animation, imgproxy will ignore this option and use all the source image pages. Use the disable_animation option to make imgproxy treat all images as not animated.

Default: 0

Pages Pro
pages:%pages
pgs:%pages

When a source image supports pagination (PDF, TIFF) or animation (GIF, WebP), this option allows specifying the number of pages to use. The pages will be stacked vertically and left-aligned.

info
If both the source and the resulting image formats supoprt animation, imgproxy will ignore this option and use all the source image pages. Use the disable_animation option to make imgproxy treat all images as not animated.

Default: 1

Disable animation Pro
disable_animation:%disable
da:%disable

When set to 1, t or true, imgproxy will treat all images as not animated. Use the page and the pages options to specify which frames imgproxy should use.

Default: false

Video thumbnail second Pro
video_thumbnail_second:%second
vts:%second

Allows redefining IMGPROXY_VIDEO_THUMBNAIL_SECOND config.

Video thumbnail keyframes Pro
video_thumbnail_keyframes:%keyframes
vtk:%keyframes

Allows redefining IMGPROXY_VIDEO_THUMBNAIL_KEYFRAMES config.

Video thumbnail tile Pro
video_thumbnail_tile:%step:%columns:%rows:%tile_width:%tile_height:%extend_tile:%trim:%fill:%focus_x:%focus_y
vtt:%step:%columns:%rows:%tile_width:%tile_height:%extend_tile:%trim:%fill:%focus_x:%focus_y

When step is not 0, imgproxy will generate a tiled sprite using the source video frames.

step: the step of timestamp (in seconds) between video frames that should be used for the sprite generation:
When step value is positive, imgproxy will use it as an absolute value
When step value is negative, imgproxy will calculate the actual step as video_duration / (columns \* rows)
columns: the number of columns in the sprite
rows: the number of rows in the sprite
tile_width, tile_height: the width and height of each tile in the sprite. imgproxy will resize each used frame to fit the provided size
extend_tile: (optional) when set to 1, t or true, imgproxy will extend each tile to the requested size using a black background
trim: (optional) when set to 1, t or true, imgproxy will trim the unused space from the sprite
fill: (optional) when set to 1, t or true, imgproxy will use the fill resizing type for the tiles
focus_x, focus_y: (optional) floating point numbers between 0 and 1 that define the coordinates of the center of the resulting tile (as in the fp gravity type). Treat 0 and 1 as right/left for x and top/bottom for y. Applicable only when fill is set. Default: 0.5:0.5
The timestamp of the first source video frame can be set using the IMGPROXY_VIDEO_THUMBNAIL_SECOND config or the video_thumbnail_second option.

You can make imgproxy use only keyframes with the IMGPROXY_VIDEO_THUMBNAIL_KEYFRAMES config or the video_thumbnail_keyframes option. Also, IMGPROXY_VIDEO_THUMBNAIL_TILE_AUTO_KEYFRAMES config makes imgproxy automatically use keyframes when the step value is greater than the interframe interval.

info
If the step value is less than the interframe interval, some frames may be used for more than one tile.

Default: 0:0:0:0:0

Video thumbnail animation Pro
video_thumbnail_animation:%step:%delay:%frames:%frame_width:%frame_height:%extend_frame:%trim:%fill:%focus_x:%focus_y
vta:%step:%delay:%frames:%frame_width:%frame_height:%extend_frame:%trim:%fill:%focus_x:%focus_y

When step is not 0, imgproxy will generate an animated image using the source video frames.

step: the step of timestamp (in seconds) between video frames that should be used for the animation generation:
When step value is positive, imgproxy will use it as an absolute value
When step value is negative, imgproxy will calculate the actual step as video_duration / frames
delay: the delay between animation frames in milliseconds
frames: the number of animation frames
frame_width, frame_height: the width and height of animation frames. imgproxy will resize each used frame to fit the provided size
extend_frame: (optional) when set to 1, t or true, imgproxy will extend each animation frame to the requested size using a black background
trim: (optional) when set to 1, t or true, imgproxy will trim the unused frames from the animation
fill: (optional) when set to 1, t or true, imgproxy will use the fill resizing type for the animation frames
focus_x, focus_y: (optional) floating point numbers between 0 and 1 that define the coordinates of the center of the resulting animation frame (as in the fp gravity type). Treat 0 and 1 as right/left for x and top/bottom for y. Applicable only when fill is set. Default: 0.5:0.5
The timestamp of the first video source frame can be set using the IMGPROXY_VIDEO_THUMBNAIL_SECOND config or the video_thumbnail_second option.

You can make imgproxy use only keyframes with the IMGPROXY_VIDEO_THUMBNAIL_KEYFRAMES config or the video_thumbnail_keyframes option. Also, IMGPROXY_VIDEO_THUMBNAIL_TILE_AUTO_KEYFRAMES config makes imgproxy automatically use keyframes when the step value is greater than the interframe interval.

info
If the step value is less than the interframe interval, some video frames may be used for more than one animation frame.

Default: 0:0:0:0:0

Fallback image URL Pro
You can use a custom fallback image by specifying its URL with the fallback_image_url processing option:

fallback_image_url:%url
fiu:%url

The value of url is the URL-safe Base64-encoded URL of the custom fallback image.

Default: blank

Skip processing
skip_processing:%extension1:%extension2:...:%extensionN
skp:%extension1:%extension2:...:%extensionN

When set, imgproxy will skip the processing of the listed formats. Also available as the IMGPROXY_SKIP_PROCESSING_FORMATS configuration.

info
Processing can only be skipped when the requested format is the same as the source format.

info
Video thumbnail processing can't be skipped.

Default: empty

Raw
raw:%raw

When set to 1, t or true, imgproxy will respond with a raw unprocessed, and unchecked source image. There are some differences between raw and skip_processing options:

While the skip_processing option has some conditions to skip the processing, the raw option allows to skip processing no matter what
With the raw option set, imgproxy doesn't check the source image's type, resolution, and file size. Basically, the raw option allows streaming of any file type
With the raw option set, imgproxy won't download the whole image to the memory. Instead, it will stream the source image directly to the response lowering memory usage
The requests with the raw option set are not limited by the IMGPROXY_WORKERS config
Default: false

Cache buster
cachebuster:%string
cb:%string

Cache buster doesn't affect image processing but its changing allows for bypassing the CDN, proxy server and browser cache. Useful when you have changed some things that are not reflected in the URL, like image quality settings, presets, or watermark data.

It's highly recommended to prefer the cachebuster option over a URL query string because that option can be properly signed.

Default: empty

Expires
expires:%timestamp
exp:%timestamp

When set, imgproxy will check the provided unix timestamp and return 404 when expired.

Default: empty

Filename
filename:%filename:%encoded
fn:%filename:%encoded

Defines a filename for the Content-Disposition header. When not specified, imgproxy will get the filename from the source URL.

filename: escaped or URL-safe Base64-encoded filename to be used in the Content-Disposition header
encoded: (optional) identifies if filename is Base64-encoded. Set it to 1, t, or true if you encoded the filename value with URL-safe Base64 encoding.
Default: empty

Return attachment
return_attachment:%return_attachment
att:%return_attachment

When set to 1, t or true, imgproxy will return attachment in the Content-Disposition header, and the browser will open a 'Save as' dialog. This is normally controlled by the IMGPROXY_RETURN_ATTACHMENT configuration but this processing option allows the configuration to be set for each request.

Preset
preset:%preset_name1:%preset_name2:...:%preset_nameN
pr:%preset_name1:%preset_name2:...:%preset_nameN

Defines a list of presets to be used by imgproxy. Feel free to use as many presets in a single URL as you need.

Read more about presets in the Presets guide.

Default: empty

Hashsum Pro
hashsum:%hashsum_type:%hashsum
hs:%hashsum_type:%hashsum

When hashsum_type is not none, imgproxy will calculate the hashsum of the source image and compare it with the provided hashsum. If they don't match, imgproxy will respond with 422.

hashsum_type: specifies the hashsum type. Available values:
none: don't check the hashsum
md5: use MD5 hashsum
sha1: use SHA1 hashsum
sha256: use SHA256 hashsum
sha512: use SHA512 hashsum
hashsum: the expected hex-encoded hashsum of the source image. If hashsum_type is none, this argument is ignored and can be omitted
Default: none

warning
Checking video file hashsums is not supported as it would require downloading the whole video file. imgproxy won't throw an error if you try to check the hashsum of a video file but it will skip the hashsum check

Max src resolution
max_src_resolution:%resolution
msr:%resolution

Allows redefining IMGPROXY_MAX_SRC_RESOLUTION config.

warning
Since this option allows redefining a security restriction, its usage is not allowed unless the IMGPROXY_ALLOW_SECURITY_OPTIONS config is set to true.

Max src file size
max_src_file_size:%size
msfs:%size

Allows redefining IMGPROXY_MAX_SRC_FILE_SIZE config.

warning
Since this option allows redefining a security restriction, its usage is not allowed unless the IMGPROXY_ALLOW_SECURITY_OPTIONS config is set to true.

Max animation frames
max_animation_frames:%size
maf:%size

Allows redefining IMGPROXY_MAX_ANIMATION_FRAMES config.

warning
Since this option allows redefining a security restriction, its usage is not allowed unless the IMGPROXY_ALLOW_SECURITY_OPTIONS config is set to true.

Max animation frame resolution
max_animation_frame_resolution:%size
mafr:%size

Allows redefining IMGPROXY_MAX_ANIMATION_FRAME_RESOLUTION config.

warning
Since this option allows redefining a security restriction, its usage is not allowed unless the IMGPROXY_ALLOW_SECURITY_OPTIONS config is set to true.

Max result dimension
max_result_dimension:%size
mrd:%size

Allows redefining IMGPROXY_MAX_RESULT_DIMENSION config.

warning
Since this option allows redefining a security restriction, its usage is not allowed unless the IMGPROXY_ALLOW_SECURITY_OPTIONS config is set to true.

Source URL
Plain
The source URL can be provided as is, prepended by the /plain/ segment:

/plain/http://example.com/images/curiosity.jpg

info
imgproxy expects the source URL to be escaped (percent-encoded) when using the /plain/ segment.

If you don't want to percent-encode all the special characters in the source URL, you can replace only the ones that can cause issues with imgproxy:

Replace % with %25 (you should do this before percent-encoding the rest of the URL)
Replace ? with %3F
Replace @ with %40
When using a plain source URL, you can specify the extension after @:

/plain/http://example.com/images/curiosity.jpg@png

Base64 encoded
The source URL can be encoded with URL-safe Base64. The encoded URL can be split with / as desired:

/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn

When using an encoded source URL, you can specify the extension after .:

/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn.png

Encrypted with AES-CBC Pro
The source URL can be encrypted with the AES-CBC algorithm, prepended by the /enc/ segment. The encrypted URL can be split with / as desired:

/enc/jwV3wUD9r4VBIzgv/ang3Hbh0vPpcm5cc/VO5rHxzonpvZjppG/2VhDnX2aariBYegH/jlhw\_-dqjXDMm4af/ZDU6y5sBog

When using an encrypted source URL, you can specify the extension after .:

/enc/jwV3wUD9r4VBIzgv/ang3Hbh0vPpcm5cc/VO5rHxzonpvZjppG/2VhDnX2aariBYegH/jlhw\_-dqjXDMm4af/ZDU6y5sBog.png

Extension
Extension specifies the format of the resulting image. Read more about image formats support here.

The extension can be omitted. In this case, imgproxy will use the source image format as resulting one. If the source image format is not supported as the resulting image, imgproxy will use jpg. You also can enable AVIF, WebP, or JPEG XL support detection to use it as the default resulting format when possible.

Best format Pro
You can use the best value for the format option or the extension to make imgproxy pick the best format for the resultant image. Check out the Best format guide to learn more.

Example
A signed imgproxy URL that uses the sharp preset, resizes http://example.com/images/curiosity.jpg to fill a 300x400 area using smart gravity without enlarging, and then converts the image to png:

http://imgproxy.example.com/AfrOrF3gWeDA6VOlDG4TzxMv39O7MXnF4CXpKUwGqRM/preset:sharp/resize:fill:300:400:0/gravity:sm/plain/http://example.com/images/curiosity.jpg@png

The same URL with shortcuts will look like this:

http://imgproxy.example.com/AfrOrF3gWeDA6VOlDG4TzxMv39O7MXnF4CXpKUwGqRM/pr:sharp/rs:fill:300:400:0/g:sm/plain/http://example.com/images/curiosity.jpg@png

The same URL with a Base64-encoded source URL will look like this:

http://imgproxy.example.com/AfrOrF3gWeDA6VOlDG4TzxMv39O7MXnF4CXpKUwGqRM/pr:sharp/rs:fill:300:400:0/g:sm/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn.png

Edit this page
