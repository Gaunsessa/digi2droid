import org.gradle.api.GradleException

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val requiredNativeAbis = listOf("armeabi-v7a")
for (abi in requiredNativeAbis) {
    val libgphoto2Prebuilt = rootProject.file("third_party/libgphoto2-android/$abi/libgphoto2.so")
    if (!libgphoto2Prebuilt.exists()) {
        throw GradleException(
            "libgphoto2 Android prebuilts are required for $abi. Initialize submodules if needed " +
                "(git submodule update --init --recursive third_party/libtool third_party/libusb third_party/libgphoto2), " +
                "then build prebuilts, e.g.:\n" +
                "  export ANDROID_NDK=\"\$HOME/Library/Android/sdk/ndk/<version>\"\n" +
                "  ./scripts/build-libgphoto2-android.sh\n" +
                "Expected file: ${libgphoto2Prebuilt.absolutePath}",
        )
    }
}

android {
    namespace = "je.ef.digi2droid"
    compileSdk = 34

    defaultConfig {
        applicationId = "je.ef.digi2droid"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
        ndk {
            abiFilters += listOf("armeabi-v7a")
        }
    }

    ndkVersion = "27.1.12297006"

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = true
    }
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
    sourceSets {
        getByName("main") {
            jniLibs.srcDir(rootProject.file("third_party/libgphoto2-android"))
            java.setSrcDirs(listOf("src/main/kotlin"))
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
}
