export default [
    {
        ignores: ["dist/**"],
    },
    {
        files: ["**/*.{js,jsx,mjs,cjs,ts,tsx}"],
        rules: {
            "react/no-unknown-property": "off",
        },
    },
];
