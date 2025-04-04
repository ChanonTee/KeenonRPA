package com.example.rpa_accessibilityservice

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.io.*
import java.net.Socket

class MyAccessibilityService : AccessibilityService() {

    private var socket: Socket? = null
    private var writer: PrintWriter? = null
    private var reader: BufferedReader? = null
    private var isRunning = true

    override fun onServiceConnected() {
        super.onServiceConnected()
        isRunning = true

        // Retrieve IP and Port from SharedPreferences
        val sharedPreferences = getSharedPreferences("RPA_PREFS", Context.MODE_PRIVATE)
        val serverIp = sharedPreferences.getString("IP", null)
        val serverPort = sharedPreferences.getInt("PORT", -1)

        if (serverIp != null && serverPort != -1) {
            connectToServer(serverIp, serverPort)
        } else {
            Log.e("AccessibilityService", "IP or Port not found in SharedPreferences")
        }
    }

    private fun attemptReconnect(ip: String, port: Int) {
        Thread {
            while (isRunning && (socket == null || !socket!!.isConnected || socket!!.isClosed)) {
                try {
                    Log.d("AccessibilityService", "Attempting to reconnect...")
                    socket = Socket(ip, port)
                    writer = PrintWriter(BufferedWriter(OutputStreamWriter(socket?.getOutputStream())), true)
                    reader = BufferedReader(InputStreamReader(socket?.getInputStream()))
                    Log.d("AccessibilityService", "Reconnected to server: $ip:$port")


                    while (isRunning) {
                        val command = reader?.readLine()
                        if (command != null) {
                            Log.d("AccessibilityService", "Received command: $command")
                            handleCommand(command)
                        } else {
                            Log.d("AccessibilityService", "Command is null, connection might be lost")
                            break
                        }
                    }
                } catch (e: IOException) {
                    Log.e("AccessibilityService", "Reconnect failed: ${e.message}")
                    Thread.sleep(10000) // wait before retry
                } finally {
                    closeConnection()
                }
            }
        }.start()
    }

    private fun connectToServer(ip: String, port: Int) {
        attemptReconnect(ip, port)
    }

    private fun closeConnection() {
        try {
            reader?.close()
            writer?.close()
            socket?.close()
            socket = null
            Log.d("AccessibilityService", "Disconnected from server")
        } catch (e: IOException) {
            Log.e("AccessibilityService", "Error closing connection: ${e.message}")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        closeConnection()
        Log.d("AccessibilityService", "Service destroyed")
    }

    override fun onInterrupt() {
        closeConnection()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Not used for this implementation
    }

    private fun handleCommand(command: String) {
        Thread {
            val rootNode = rootInActiveWindow
            if (rootNode == null) {
                sendResponse("No active window found.")
                return@Thread
            }

            when (command) {
                "ping" -> {
                    sendResponse("pong")
                }
                "goHome", "goBack", "showRecents" -> performGlobalActionByCommand(command)
                "scrollUp", "scrollDown" -> performScroll(rootNode, command)

                "getFullUI" -> {
                    val hierarchy = buildFullHierarchy(rootNode)
                    sendLargeResponse(hierarchy)  // Send FullHierarchy to Python server
                }
                "clickBackButton" -> {
                    clickBackButton(rootNode) // Handle back button click
                }
                // Default behavior for finding and performing action
                else -> findAndPerformActionOnMainThread(rootNode, command)
            }
        }.start()
    }

    private fun performGlobalActionByCommand(command: String) {
        when (command) {
            "goHome" -> {
                performGlobalAction(GLOBAL_ACTION_HOME)
                sendResponse("Performed action: Home")
            }
            "goBack" -> {
                performGlobalAction(GLOBAL_ACTION_BACK)
                sendResponse("Performed action: Back")
            }
            "showRecents" -> {
                performGlobalAction(GLOBAL_ACTION_RECENTS)
                sendResponse("Performed action: Show Recent Apps")
            }
            else -> {
                Log.e("AccessibilityService", "Invalid global action command: $command")
                sendResponse("Invalid global action command: $command")
            }
        }
    }

    // Helper to find and perform action on the main thread
    private fun findAndPerformActionOnMainThread(rootNode: AccessibilityNodeInfo, command: String) {
        Handler(Looper.getMainLooper()).post {
            findAndPerformAction(rootNode, command)
        }
    }


    private fun logFullHierarchy(node: AccessibilityNodeInfo?, depth: Int = 0) {
        if (node == null) {
            Log.e("UIHierarchy", "Node is null at depth $depth")
            return
        }

        val prefix = " ".repeat(depth * 2)
        Log.d(
            "UIHierarchy",
            "$prefix Node: ${node.className}," +
                    "Text: ${node.text}," +
                    "Clickable: ${node.isClickable}," +
                    "Visible: ${node.isVisibleToUser}," +
                    "Children: ${node.childCount}," +
                    "Scrollable: ${node.isScrollable}"
        )

        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child == null) {
                Log.e("UIHierarchy", "$prefix Child at index $i is null.")
                continue
            }
            logFullHierarchy(child, depth + 1)
        }
    }

    private fun buildFullHierarchy(node: AccessibilityNodeInfo?, depth: Int = 0, sb: StringBuilder = StringBuilder()): String {
        if (node == null) return sb.toString()

        val prefix = " ".repeat(depth * 2)
        sb.append(
            "$prefix Node: ${node.className}," +
                    " Text: ${node.text}," +
                    " Clickable: ${node.isClickable}," +
                    " Visible: ${node.isVisibleToUser}," +
                    " Children: ${node.childCount}," +
                    " Scrollable: ${node.isScrollable}\n"
        )

        for (i in 0 until node.childCount) {
            buildFullHierarchy(node.getChild(i), depth + 1, sb)
        }
        return sb.toString()
    }


    private fun findNodeByPartialText(rootNode: AccessibilityNodeInfo, keyword: String): AccessibilityNodeInfo? {
        val queue = ArrayDeque<AccessibilityNodeInfo>()
        queue.add(rootNode)

        while (queue.isNotEmpty()) {
            val node = queue.removeFirst()

            // use If want sensitive case
            // if (node.text?.contains(keyword, true) == true || node.contentDescription?.contains(keyword, true) == true) {
            if (node.text?.equals(keyword) == true) {
                return node
            }

            // Add children to the queue
            for (i in 0 until node.childCount) {
                node.getChild(i)?.let { queue.add(it) }
            }
        }
        return null
    }

    private fun findAndPerformAction(rootNode: AccessibilityNodeInfo, command: String) {
        val targetNode = findNodeByPartialText(rootNode, command)

        if (targetNode != null) {
            // Log the node regardless of visibility
            logNode(targetNode)

            // Perform action if node is clickable
            if (targetNode.isClickable) {
                targetNode.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                sendResponse("Command executed: $command")

                // send FullHierarchy after Click
                // val updatedHierarchy = buildFullHierarchy(rootInActiveWindow)
                // sendResponse("Updated UI Hierarchy:\n$updatedHierarchy")
            } else {
                // Traverse up the hierarchy to find a clickable parent
                var parentNode = targetNode.parent
                while (parentNode != null) {
                    if (parentNode.isClickable) {
                        parentNode.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        sendResponse("Command executed: $command via parent node")

                        // send FullHierarchy after Click
                        //  val updatedHierarchy = buildFullHierarchy(rootInActiveWindow)
                        //  sendResponse("Updated UI Hierarchy:\n$updatedHierarchy")
                        return
                    }
                    parentNode = parentNode.parent
                }
                Log.e("AccessibilityService", "No clickable parent found for command: $command")
            }
        } else {
            Log.e("AccessibilityService", "Command not found in UI: $command")
            sendResponse("Command not found in UI: $command")
        }
    }

    // Log the node regardless of visibility
    private fun logNode(node: AccessibilityNodeInfo) {
        Log.d("AccessibilityService",
            "Node Text: ${node.text} | " +
                    "Class: ${node.className} | " +
                    "Clickable: ${node.isClickable} | " +
                    "Visible: ${node.isVisibleToUser} |" +
                    "Scrollable: ${node.isScrollable}")
    }

    // If want to click only UI visible to user
    private fun findAndPerformActionV2(rootNode: AccessibilityNodeInfo, command: String) {
        val nodes = rootNode.findAccessibilityNodeInfosByText(command)
        if (nodes.isNotEmpty()) {
            val targetNode = nodes[0]

            if (targetNode.isVisibleToUser && targetNode.isClickable) {
                targetNode.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                sendResponse("Command executed: $command")
            } else {
                // Traverse up the hierarchy to find a clickable parent
                var parentNode = targetNode.parent
                while (parentNode != null) {
                    if (parentNode.isVisibleToUser && parentNode.isClickable) {
                        parentNode.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        sendResponse("Command executed: $command via parent node")
                        return
                    }
                    parentNode = parentNode.parent
                }
                Log.e("AccessibilityService", "No clickable parent found for command: $command")
            }
        } else {
            Log.e("AccessibilityService", "Command not found in UI: $command")
        }
    }

    private fun clickBackButton(rootNode: AccessibilityNodeInfo) {
        val queue = ArrayDeque<AccessibilityNodeInfo>()
        queue.add(rootNode)

        while (queue.isNotEmpty()) {
            val node = queue.removeFirst()

            // check clickable ImageButton
            if (node.className == "android.widget.ImageView" && node.isClickable) {
                Log.d("AccessibilityService", "Found ImageButton, performing click...")
                node.performAction(AccessibilityNodeInfo.ACTION_CLICK)

                // send FullHierarchy after
                // val updatedHierarchy = buildFullHierarchy(rootInActiveWindow)
                sendResponse("Clicked Back Button.")
                return
            }

            // add node into queue
            for (i in 0 until node.childCount) {
                node.getChild(i)?.let { queue.add(it) }
            }
        }
        Log.e("AccessibilityService", "Back Button (ImageButton) not found.")
        sendResponse("Back Button (ImageButton) not found.")
    }

    private fun performScroll(rootNode: AccessibilityNodeInfo, direction: String) {
        try {
            val action = when (direction) {
                "scrollUp" -> AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
                "scrollDown" -> AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
                else -> {
                    sendResponse("Invalid scroll command: $direction")
                    return
                }
            }

            var success = false
            val stack = ArrayDeque<AccessibilityNodeInfo>()
            stack.addFirst(rootNode)

            while (stack.isNotEmpty()) {
                val node = stack.removeFirst()

                Log.d("AccessibilityService", "Node: ${node.className} | Scrollable: ${node.isScrollable}")

                if (node.isScrollable) {
                    success = node.performAction(action)
                    break
                }

                for (i in 0 until node.childCount) {
                    stack.addFirst(node.getChild(i))
                }
            }

            if (success) {
                sendResponse("Scroll $direction completed successfully")
            } else {
                sendResponse("No scrollable node found")
            }
        } catch (e: Exception) {
            sendResponse("Error executing scroll: ${e.message}")
        }
    }

    private fun sendResponse(response: String) {
        Thread {
            try {
                writer?.println(response)
                writer?.flush()
                Log.d("AccessibilityService", "Response sent: $response")
            } catch (e: Exception) {
                Log.e("AccessibilityService", "Error sending response: ${e.message}")
            }
        }.start()
    }

    private fun sendLargeResponse(response: String) {
        val chunkSize = 4000  // 4KB chunk size
        var index = 0
        while (index < response.length) {
            val chunk = response.substring(index, minOf(index + chunkSize, response.length))
            sendResponseToSocket(chunk)  // Send the chunk
            Thread.sleep(10)  // Slight delay to avoid socket overflow
            index += chunkSize
        }
        sendResponseToSocket("[END]")  // Signal the end of the message
    }

    private fun sendResponseToSocket(chunk: String) {
        try {
            socket?.getOutputStream()?.let { outputStream ->
                outputStream.write((chunk + "\n").toByteArray(Charsets.UTF_8))
                outputStream.flush()
            }
            Log.d("AccessibilityService", "Chunk sent: $chunk")
        } catch (e: Exception) {
            Log.e("AccessibilityService", "Error sending chunk: ${e.message}")
        }
    }
}