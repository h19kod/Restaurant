export default function Reports() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">التقارير</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-md">
          <h2 className="text-xl font-bold text-gray-800 mb-4">المبيعات الأسبوعية</h2>
          <div className="h-64 flex items-end justify-between gap-2">
            {[1200, 1900, 1500, 2100, 1800, 2400, 2200].map((val, i) => (
              <div key={i} className="flex-1 bg-blue-500 rounded-t" style={{ height: `${val / 24}%` }} />
            ))}
          </div>
          <div className="flex justify-between mt-2 text-sm text-gray-500">
            <span>السبت</span><span>الأحد</span><span>الاثنين</span><span>الثلاثاء</span><span>الأربعاء</span><span>الخميس</span><span>الجمعة</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-md">
          <h2 className="text-xl font-bold text-gray-800 mb-4">الأصناف الأكثر طلباً</h2>
          <div className="space-y-4">
            {[
              { name: 'برجر دجاج', count: 45 },
              { name: 'بيتزا مارغريتا', count: 38 },
              { name: 'سلطة سيزر', count: 32 },
              { name: 'باستا ألفريدو', count: 28 },
            ].map((item) => (
              <div key={item.name}>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-700">{item.name}</span>
                  <span className="text-gray-500">{item.count} طلب</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${item.count / 0.45}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
