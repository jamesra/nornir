MAGICKVERSION=7.1.1-27

mkdir image-magick

cd image-magick

apt-get update && apt-get install -y wget && \
    apt-get install -y autoconf pkg-config

apt-get update && apt-get install -y wget && \
    apt-get install -y build-essential curl libpng-dev && \
    wget https://github.com/ImageMagick/ImageMagick/archive/refs/tags/${MAGICKVERSION}.tar.gz && \
    tar xzf ${MAGICKVERSION}.tar.gz && \
    rm ${MAGICKVERSION}.tar.gz && \
    apt-get clean && \
    apt-get autoremove

sh ./ImageMagick-${MAGICKVERSION}/configure --prefix=/usr/local --with-bzlib=yes --with-fontconfig=yes --with-freetype=yes --with-gslib=yes --with-gvc=yes --with-jpeg=yes --with-jp2=yes --with-png=yes --with-tiff=yes --with-xml=yes --with-gs-font-dir=yes && \
    make -j && make install && ldconfig /usr/local/lib/

cd ..

rm -rf image-magick/