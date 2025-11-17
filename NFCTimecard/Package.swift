// swift-tools-version: 5.7
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "NFCTimecard",
    platforms: [
        .iOS(.v15)
    ],
    products: [
        .library(
            name: "NFCTimecard",
            targets: ["NFCTimecard"]),
    ],
    dependencies: [
        // 依存関係は現在なし（将来的に追加可能）
    ],
    targets: [
        .target(
            name: "NFCTimecard",
            dependencies: [],
            path: ".",
            exclude: ["Tests"],
            sources: [
                "App",
                "Views",
                "Managers",
                "Models",
                "Utils"
            ],
        ),
        .testTarget(
            name: "NFCTimecardTests",
            dependencies: ["NFCTimecard"],
            path: "Tests"
        ),
    ]
)
