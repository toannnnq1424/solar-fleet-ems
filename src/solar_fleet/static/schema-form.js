// Forms are generated only from a reviewed, bounded device schema; the server remains authoritative.
import { l } from "./i18n.js";

export function schemaControl(schema, ui, depth = 0) {
  const { e, div, input, select, field, btn } = ui;
  if (
    depth > 5 ||
    !schema ||
    schema.$ref ||
    schema.oneOf ||
    schema.anyOf ||
    schema.allOf ||
    schema.if
  )
    throw new Error(
      l(
        "Profile cần form riêng cho cấu trúc này.",
        "This profile requires a dedicated form for this structure.",
      ),
    );
  if (schema.const !== undefined)
    return {
      node: e("span", JSON.stringify(schema.const)),
      read: () => schema.const,
    };
  if (schema.enum) {
    const node = select(
      schema.enum.map((v, i) => [
        String(i),
        typeof v === "object" ? JSON.stringify(v) : String(v),
      ]),
    );
    return { node, read: () => schema.enum[Number(node.value)] };
  }
  if (schema.type === "object") {
    const node = div("form-grid"),
      controls = [];
    for (const [key, child] of Object.entries(schema.properties || {})) {
      const c = schemaControl(child, ui, depth + 1),
        required = (schema.required || []).includes(key),
        enabled = input("checkbox");
      enabled.checked = required;
      const container = div("stack", field(child.title || key, c.node));
      if (!required) {
        container.prepend(
          field(l("Có dùng ", "Include ") + (child.title || key), enabled),
        );
        c.node.hidden = true;
        enabled.onchange = () => {
          c.node.hidden = !enabled.checked;
        };
      }
      controls.push({ key, c, enabled, required });
      node.append(container);
    }
    if (
      (schema.required || []).some(
        (key) => !controls.some((c) => c.key === key),
      )
    )
      throw new Error(
        l(
          "Thiếu định nghĩa trường bắt buộc.",
          "Required field schema is missing.",
        ),
      );
    return {
      node,
      read: () =>
        Object.fromEntries(
          controls
            .filter((c) => c.required || c.enabled.checked)
            .map((c) => [c.key, c.c.read()]),
        ),
    };
  }
  if (schema.type === "array") {
    if (
      !Number.isInteger(schema.maxItems) ||
      schema.maxItems > 168 ||
      !schema.items ||
      Array.isArray(schema.items)
    )
      throw new Error(
        l(
          "Cần giới hạn số dòng đúng model.",
          "A bounded model-specific row count is required.",
        ),
      );
    const node = div("stack"),
      list = div("stack"),
      entries = [];
    const addRow = () => {
      if (entries.length >= schema.maxItems) return;
      const c = schemaControl(schema.items, ui, depth + 1),
        row = div("array-row", c.node);
      row.append(
        btn(l("Xóa dòng", "Remove row"), () => {
          if (entries.length <= (schema.minItems || 0)) return;
          entries.splice(entries.indexOf(c), 1);
          row.remove();
        }),
      );
      entries.push(c);
      list.append(row);
    };
    for (let i = 0; i < (schema.minItems || 0); i++) addRow();
    node.append(list, btn(l("+ Thêm dòng", "+ Add row"), addRow));
    return { node, read: () => entries.map((c) => c.read()) };
  }
  if (schema.type === "boolean") {
    const node = input("checkbox");
    return { node, read: () => node.checked };
  }
  if (["integer", "number"].includes(schema.type)) {
    if (schema.minimum == null || schema.maximum == null)
      throw new Error(
        l(
          "Cần giới hạn đã xác minh cho thông số.",
          "Verified parameter bounds are required.",
        ),
      );
    const node = input("number", schema.default ?? schema.minimum);
    node.min = schema.minimum;
    node.max = schema.maximum;
    node.step = schema.multipleOf || (schema.type === "integer" ? 1 : "any");
    return {
      node,
      read: () => {
        if (node.value === "" || !node.checkValidity())
          throw new Error(
            l(
              "Kiểm tra giá trị và giới hạn.",
              "Check the value and its limits.",
            ),
          );
        return Number(node.value);
      },
    };
  }
  if (schema.type === "string") {
    const node = input("text", schema.default || "");
    node.maxLength = schema.maxLength || 256;
    node.minLength = schema.minLength || 0;
    if (schema.pattern) node.pattern = schema.pattern;
    return {
      node,
      read: () => {
        if (!node.checkValidity())
          throw new Error(
            l("Thông số không đúng định dạng.", "Parameter format is invalid."),
          );
        return node.value;
      },
    };
  }
  throw new Error(
    l(
      "Kiểu thông số chưa có form được hỗ trợ.",
      "No supported form for this parameter type.",
    ),
  );
}
