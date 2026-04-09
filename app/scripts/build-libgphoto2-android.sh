#!/usr/bin/env bash
# Cross-compile libltdl, libusb-1.0, and libgphoto2 for Android, apply the flat
# camlib/iolib layout from libgphoto2's Android support, then copy artifacts to:
#   third_party/libgphoto2-android/<ANDROID_ABI>/*.so
#   third_party/libgphoto2-android/include/gphoto2/
#
# ANDROID_ABI defaults to armeabi-v7a (32-bit ARM). For 64-bit ARM use:
#   ANDROID_ABI=arm64-v8a ./scripts/build-libgphoto2-android.sh
#
# All sources come from git submodules under third_party/:
#   libtool   — build libltdl from libtool/libltdl (GNU libtool, pinned to v2.4.7 in the superproject)
#   libusb    — libusb 1.0 (pinned to v1.0.27)
#   libgphoto2
#
# Requirements: ANDROID_NDK (or ANDROID_HOME), autoconf, automake, libtool, pkg-config,
# git, GNU make, bash 4+.
#
# First-time repo setup:
#   git submodule update --init --recursive third_party/libtool third_party/libusb third_party/libgphoto2
#
# Usage (from repo root):
#   export ANDROID_NDK="$HOME/Library/Android/sdk/ndk/27.1.12297006"
#   ./scripts/build-libgphoto2-android.sh

set -euo pipefail

ANDROID_ABI="${ANDROID_ABI:-armeabi-v7a}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIBTOOL_SRC="${ROOT}/third_party/libtool"
LIBLTDL_SRC="${LIBTOOL_SRC}/libltdl"
LIBUSB_SRC="${ROOT}/third_party/libusb"
LIBGPHOTO2_SRC="${ROOT}/third_party/libgphoto2"
WORK="${ROOT}/.gphoto-android-build"
PREFIX="${WORK}/prefix-${ANDROID_ABI}"
OUT_ABI="${ROOT}/third_party/libgphoto2-android/${ANDROID_ABI}"
OUT_INC="${ROOT}/third_party/libgphoto2-android/include"
LIBLTDL_BUILD="${WORK}/libltdl-build-${ANDROID_ABI}"
LIBUSB_BUILD="${WORK}/libusb-build-${ANDROID_ABI}"
LIBGPHOTO2_BUILD="${WORK}/libgphoto2-build-${ANDROID_ABI}"
API="${API:-24}"

init_submodules() {
  if [[ -d "${ROOT}/.git" ]] && [[ -f "${ROOT}/.gitmodules" ]]; then
    echo "Initializing git submodules (libtool, libusb, libgphoto2)..."
    git -C "$ROOT" submodule update --init --recursive \
      third_party/libtool \
      third_party/libusb \
      third_party/libgphoto2
  fi
  if [[ ! -f "${LIBLTDL_SRC}/configure.ac" ]]; then
    echo "Missing ${LIBLTDL_SRC}. Run: git submodule update --init --recursive third_party/libtool" >&2
    exit 1
  fi
  if [[ ! -f "${LIBUSB_SRC}/configure.ac" ]]; then
    echo "Missing ${LIBUSB_SRC}. Run: git submodule update --init --recursive third_party/libusb" >&2
    exit 1
  fi
  if [[ ! -f "${LIBGPHOTO2_SRC}/configure.ac" ]]; then
    echo "Missing ${LIBGPHOTO2_SRC}. Run: git submodule update --init --recursive third_party/libgphoto2" >&2
    exit 1
  fi
}

if [[ -z "${ANDROID_NDK:-}" && -n "${ANDROID_HOME:-}" ]]; then
  ANDROID_NDK="$(ls -d "${ANDROID_HOME}/ndk/"* 2>/dev/null | sort -V | tail -1)"
fi
if [[ -z "${ANDROID_NDK:-}" ]]; then
  echo "Set ANDROID_NDK to your NDK root (e.g. \$HOME/Library/Android/sdk/ndk/27.1.12297006)." >&2
  exit 1
fi

HOST_OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
HOST_ARCH="$(uname -m)"
NDK_PREBUILT_CANDIDATES=()
if [[ "$HOST_OS" == "darwin" ]]; then
  if [[ "$HOST_ARCH" == "arm64" ]]; then
    NDK_PREBUILT_CANDIDATES=(darwin-arm64 darwin-x86_64)
  else
    NDK_PREBUILT_CANDIDATES=(darwin-x86_64)
  fi
else
  NDK_PREBUILT_CANDIDATES=(linux-x86_64)
fi

TOOLCHAIN=""
for cand in "${NDK_PREBUILT_CANDIDATES[@]}"; do
  if [[ -d "${ANDROID_NDK}/toolchains/llvm/prebuilt/${cand}" ]]; then
    TOOLCHAIN="${ANDROID_NDK}/toolchains/llvm/prebuilt/${cand}"
    break
  fi
done
if [[ -z "$TOOLCHAIN" ]]; then
  echo "NDK toolchain not found under ${ANDROID_NDK}/toolchains/llvm/prebuilt/ (tried: ${NDK_PREBUILT_CANDIDATES[*]})" >&2
  exit 1
fi

export PATH="${TOOLCHAIN}/bin:${PATH}"
export AR=llvm-ar
export RANLIB=llvm-ranlib
export STRIP=llvm-strip

case "${ANDROID_ABI}" in
  arm64-v8a)
    export CC="${TOOLCHAIN}/bin/aarch64-linux-android${API}-clang"
    export CXX="${TOOLCHAIN}/bin/aarch64-linux-android${API}-clang++"
    TRIPLE="aarch64-linux-android"
    ;;
  armeabi-v7a)
    export CC="${TOOLCHAIN}/bin/armv7a-linux-androideabi${API}-clang"
    export CXX="${TOOLCHAIN}/bin/armv7a-linux-androideabi${API}-clang++"
    TRIPLE="arm-linux-androideabi"
    ;;
  *)
    echo "Unsupported ANDROID_ABI=${ANDROID_ABI} (use armeabi-v7a or arm64-v8a)" >&2
    exit 1
    ;;
esac

mkdir -p "$WORK" "$PREFIX" "$OUT_ABI" "$OUT_INC"

init_submodules

export PKG_CONFIG_PATH="${PREFIX}/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="${PREFIX}/lib/pkgconfig"
export CFLAGS="-fPIC -fPIE -O2"
export CXXFLAGS="-fPIC -fPIE -O2"
export LDFLAGS="-pie -L${PREFIX}/lib"

fix_libtool_empty_archive_cmds() {
  local dir="$1"
  if [[ ! -f "${dir}/libtool" ]]; then
    return 0
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' 's/^archive_cmds=""/archive_cmds="\\\$CC -shared \\\$pic_flag \\\$libobjs \\\$deplibs \\\$compiler_flags \\\$wl-soname \\\$wl\\\$soname -o \\\$lib"/' "${dir}/libtool"
  else
    sed -i 's/^archive_cmds=""/archive_cmds="\\\$CC -shared \\\$pic_flag \\\$libobjs \\\$deplibs \\\$compiler_flags \\\$wl-soname \\\$wl\\\$soname -o \\\$lib"/' "${dir}/libtool"
  fi
}

build_libltdl() {
  if [[ ! -f "${LIBLTDL_SRC}/configure" ]]; then
    (cd "${LIBLTDL_SRC}" && autoreconf -fi)
  fi
  rm -rf "${LIBLTDL_BUILD}"
  mkdir -p "${LIBLTDL_BUILD}"
  pushd "${LIBLTDL_BUILD}" >/dev/null
  "${LIBLTDL_SRC}/configure" \
    --host="${TRIPLE}" \
    --prefix="${PREFIX}" \
    --enable-shared \
    --disable-static \
    --enable-ltdl-install
  make -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"
  make install
  popd >/dev/null
}

build_libusb() {
  if [[ ! -f "${LIBUSB_SRC}/configure" ]]; then
    (cd "${LIBUSB_SRC}" && autoreconf -fi)
  fi
  rm -rf "${LIBUSB_BUILD}"
  mkdir -p "${LIBUSB_BUILD}"
  pushd "${LIBUSB_BUILD}" >/dev/null
  "${LIBUSB_SRC}/configure" \
    --host="${TRIPLE}" \
    --prefix="${PREFIX}" \
    --disable-udev \
    --enable-shared \
    --disable-static
  make -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"
  make install
  popd >/dev/null
}

build_libgphoto2() {
  rm -rf "${LIBGPHOTO2_BUILD}"
  mkdir -p "${LIBGPHOTO2_BUILD}"
  if [[ ! -f "${LIBGPHOTO2_SRC}/configure" ]]; then
    (cd "${LIBGPHOTO2_SRC}" && autoreconf -fi)
  fi
  pushd "${LIBGPHOTO2_BUILD}" >/dev/null
  # Cross-compiling: libltdl is in PREFIX; autodetection looks at host paths without this.
  export LTDLINCL="-I${PREFIX}/include"
  export LIBLTDL="-L${PREFIX}/lib -lltdl"
  export LIBUSB_CFLAGS="-I${PREFIX}/include/libusb-1.0"
  export LIBUSB_LIBS="-L${PREFIX}/lib -lusb-1.0"
  "${LIBGPHOTO2_SRC}/configure" \
    --host="${TRIPLE}" \
    --prefix="${PREFIX}" \
    --with-libxml-2.0=no \
    --with-libcurl=no \
    --with-gdlib=no \
    --with-libexif=no \
    --without-libjpeg \
    --disable-static \
    --enable-shared \
    --disable-rpath
  fix_libtool_empty_archive_cmds "."
  if [[ -f libgphoto2_port/libtool ]]; then
    fix_libtool_empty_archive_cmds "libgphoto2_port"
  fi
  make -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"
  make install
  popd >/dev/null

  local pfx="${PREFIX}"
  shopt -s nullglob
  for f in "${pfx}/lib/libgphoto2/"*/*.so; do
    mv -f "$f" "${pfx}/lib/libgphoto2_camlib_$(basename "$f")"
  done
  for f in "${pfx}/lib/libgphoto2_port/"*/*.so; do
    mv -f "$f" "${pfx}/lib/libgphoto2_port_iolib_$(basename "$f")"
  done
  shopt -u nullglob
}

install_into_project() {
  rm -f "${OUT_ABI}/"*.so
  cp -f "${PREFIX}/lib/libgphoto2.so" "${OUT_ABI}/"
  cp -f "${PREFIX}/lib/libgphoto2_port.so" "${OUT_ABI}/"
  cp -f "${PREFIX}/lib/libusb-1.0.so" "${OUT_ABI}/"
  cp -f "${PREFIX}/lib/libltdl.so" "${OUT_ABI}/"
  shopt -s nullglob
  for f in "${PREFIX}/lib"/libgphoto2_camlib_*.so; do
    cp -f "$f" "${OUT_ABI}/"
  done
  for f in "${PREFIX}/lib"/libgphoto2_port_iolib_*.so; do
    cp -f "$f" "${OUT_ABI}/"
  done
  shopt -u nullglob

  rm -rf "${OUT_INC}"
  mkdir -p "${OUT_INC}"
  cp -R "${PREFIX}/include/gphoto2" "${OUT_INC}/"
}

echo "ANDROID_ABI=${ANDROID_ABI} (CC=${CC})"
echo "Building libltdl from submodule ${LIBLTDL_SRC} (out-of-tree in ${LIBLTDL_BUILD})..."
build_libltdl

echo "Building libusb from submodule ${LIBUSB_SRC} (out-of-tree in ${LIBUSB_BUILD})..."
build_libusb

echo "Building libgphoto2 from submodule ${LIBGPHOTO2_SRC} (out-of-tree in ${LIBGPHOTO2_BUILD})..."
build_libgphoto2

echo "Installing into ${ROOT}/third_party/libgphoto2-android/${ANDROID_ABI}/ ..."
install_into_project

echo "Done. Rebuild the app: ./gradlew :app:assembleDebug"
