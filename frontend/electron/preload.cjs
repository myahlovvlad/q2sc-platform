const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('q2scDesktop', {
  platform: process.platform,
  version: process.versions.electron,
  runtime: 'electron',
})
