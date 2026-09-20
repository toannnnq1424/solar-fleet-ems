// Parse every shipped ES module, including imports; never execute application code.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const directory = path.join(__dirname, "../src/solar_fleet/static");
const files = fs.readdirSync(directory).filter((f) => f.endsWith(".js"));
async function check() {
  const modules = new Map();
  for (const file of files) {
    modules.set(
      file,
      new vm.SourceTextModule(
        fs.readFileSync(path.join(directory, file), "utf8"),
        { identifier: file },
      ),
    );
    process.stdout.write(`${file}: syntax valid\n`);
  }
  for (const module of modules.values()) {
    if (module.status !== "unlinked") continue;
    await module.link((specifier) => {
      if (!specifier.startsWith("./") || !modules.has(specifier.slice(2)))
        throw new Error(`Unknown local module: ${specifier}`);
      return modules.get(specifier.slice(2));
    });
  }
  process.stdout.write(
    "All local module imports and exports linked. Application code was not executed.\n",
  );
}
check().catch((error) => {
  process.stderr.write(String(error.stack) + "\n");
  process.exitCode = 1;
});
