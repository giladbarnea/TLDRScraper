import Foundation
import JavaScriptCore

enum ReducerBridgeError: Error {
    case missingJavaScriptFile(String)
    case scriptEvaluationFailed(String)
    case reducerFunctionMissing(String)
    case dispatchFailed
}

final class ReducerBridge {
    private let context: JSContext
    private let reducerFunctionName: String

    init(reducerFunctionName: String, scriptNames: [String], bundle: Bundle = .main) throws {
        self.reducerFunctionName = reducerFunctionName
        guard let jsContext = JSContext() else {
            throw ReducerBridgeError.dispatchFailed
        }

        self.context = jsContext

        for scriptName in scriptNames {
            guard let scriptPath = bundle.path(forResource: scriptName, ofType: "js", inDirectory: "reducers") else {
                throw ReducerBridgeError.missingJavaScriptFile(scriptName)
            }

            let scriptContents = try String(contentsOfFile: scriptPath, encoding: .utf8)
            let transformedScript = Self.transformModuleSyntax(scriptContents)
            jsContext.exception = nil
            _ = jsContext.evaluateScript(transformedScript)

            if jsContext.exception != nil {
                throw ReducerBridgeError.scriptEvaluationFailed(scriptName)
            }
        }

        guard jsContext.objectForKeyedSubscript(reducerFunctionName)?.isUndefined == false else {
            throw ReducerBridgeError.reducerFunctionMissing(reducerFunctionName)
        }
    }

    func dispatch(state: [String: Any], event: [String: Any]) throws -> [String: Any] {
        guard let reducerFunction = context.objectForKeyedSubscript(reducerFunctionName) else {
            throw ReducerBridgeError.reducerFunctionMissing(reducerFunctionName)
        }

        context.exception = nil
        guard let result = reducerFunction.call(withArguments: [state, event]),
              let dictionary = result.toDictionary() as? [String: Any] else {
            throw ReducerBridgeError.dispatchFailed
        }

        if context.exception != nil {
            throw ReducerBridgeError.dispatchFailed
        }

        return dictionary
    }

    private static func transformModuleSyntax(_ script: String) -> String {
        let declarationPattern = "(^|\\n)\\s*export\\s+(const|function|class)\\s+"
        let declarationRegex = try! NSRegularExpression(pattern: declarationPattern, options: [])
        let declarationRange = NSRange(script.startIndex..<script.endIndex, in: script)
        let withoutDeclarationExports = declarationRegex.stringByReplacingMatches(
            in: script,
            options: [],
            range: declarationRange,
            withTemplate: "$1$2 "
        )

        let exportListPattern = "(^|\\n)\\s*export\\s*\\{[^}]*\\}\\s*;?"
        let exportListRegex = try! NSRegularExpression(pattern: exportListPattern, options: [])
        let exportListRange = NSRange(withoutDeclarationExports.startIndex..<withoutDeclarationExports.endIndex, in: withoutDeclarationExports)
        return exportListRegex.stringByReplacingMatches(
            in: withoutDeclarationExports,
            options: [],
            range: exportListRange,
            withTemplate: "$1"
        )
    }
}
