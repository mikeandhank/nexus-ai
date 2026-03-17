package com.nexusos.app

import android.app.Application

class NexusOSApp : Application() {
    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    companion object {
        lateinit var instance: NexusOSApp
            private set
    }
}
