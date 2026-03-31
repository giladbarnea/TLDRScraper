import SwiftUI

struct ContentView: View {
    var body: some View {
        NavigationStack {
            VStack {
                Image(systemName: "newspaper")
                    .imageScale(.large)
                    .foregroundStyle(.tint)
                Text("TLDRScraper")
                    .font(.largeTitle)
                    .bold()
                Text("Your tech newsletter digest")
                    .foregroundStyle(.secondary)
            }
            .padding()
            .navigationTitle("TLDR")
        }
    }
}

#Preview {
    ContentView()
}
