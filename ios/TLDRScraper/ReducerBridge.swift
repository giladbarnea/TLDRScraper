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
            let result = jsContext.evaluateScript(scriptContents)
            if result?.isUndefined == true {
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

        guard let result = reducerFunction.call(withArguments: [state, event]),
              let dictionary = result.toDictionary() as? [String: Any] else {
            throw ReducerBridgeError.dispatchFailed
        }

        return dictionary
    }
}
