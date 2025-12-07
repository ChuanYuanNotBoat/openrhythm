use pyo3::prelude::*;
use pyo3::types::{PyList, PyDict};
use pyo3::PyObject;
use crate::chart::ChartManager;

#[pyclass]
pub struct PyChartManager {
    inner: ChartManager,
}

#[pymethods]
impl PyChartManager {
    #[new]
    fn new() -> PyResult<Self> {
        let manager = ChartManager::new()
            .map_err(|e| pyo3::exceptions::PyException::new_err(format!("{}", e)))?;
        
        Ok(Self { inner: manager })
    }
    
    fn import_mcz(&self, py: Python, mcz_path: String) -> PyResult<PyObject> {
        // Run synchronously under the GIL for now to avoid threading/GIL issues.
        let charts = self.inner.import_mcz_file(mcz_path)
            .map_err(|e| pyo3::exceptions::PyException::new_err(format!("{}", e)))?;

        // 转换为Python列表
        let py_charts = PyList::empty(py);

        for chart in charts {
            let dict = PyDict::new(py);
            dict.set_item("id", chart.id)?;
            dict.set_item("title", chart.title)?;
            dict.set_item("artist", chart.artist)?;
            dict.set_item("creator", chart.creator)?;
            dict.set_item("version", chart.version)?;
            dict.set_item("bpm", chart.bpm)?;

            // 转换难度信息
            let py_difficulties = PyList::empty(py);
            for diff in chart.difficulties {
                let diff_dict = PyDict::new(py);
                diff_dict.set_item("name", diff.name)?;
                diff_dict.set_item("level", diff.level)?;
                diff_dict.set_item("note_count", diff.note_count)?;
                diff_dict.set_item("duration", diff.duration)?;
                py_difficulties.append(diff_dict)?;
            }
            dict.set_item("difficulties", py_difficulties)?;

            py_charts.append(dict)?;
        }

        Ok(py_charts.into())
    }
    
    fn get_all_charts(&self, py: Python) -> PyResult<PyObject> {
        let charts = self.inner.get_all_charts();
        
        let py_charts = PyList::empty(py);
        for chart in charts {
            let dict = PyDict::new(py);
            dict.set_item("id", chart.id)?;
            dict.set_item("title", chart.title)?;
            dict.set_item("artist", chart.artist)?;
            dict.set_item("creator", chart.creator)?;
            dict.set_item("play_count", chart.play_count)?;
            dict.set_item("rating", chart.rating)?;
            
            py_charts.append(dict)?;
        }
        
        Ok(py_charts.into())
    }
    
    fn search_charts(&self, py: Python, query: String) -> PyResult<PyObject> {
        let charts = self.inner.search_charts(&query);
        
        let py_charts = PyList::empty(py);
        for chart in charts {
            let dict = PyDict::new(py);
            dict.set_item("id", chart.id)?;
            dict.set_item("title", chart.title)?;
            dict.set_item("artist", chart.artist)?;
            dict.set_item("creator", chart.creator)?;
            dict.set_item("play_count", chart.play_count)?;
            
            py_charts.append(dict)?;
        }
        
        Ok(py_charts.into())
    }
    
    fn record_play(&self, chart_id: String) -> PyResult<()> {
        self.inner.record_play(&chart_id)
            .map_err(|e| pyo3::exceptions::PyException::new_err(format!("{}", e)))
    }
    
    fn set_rating(&self, chart_id: String, rating: f32) -> PyResult<()> {
        self.inner.set_rating(&chart_id, rating)
            .map_err(|e| pyo3::exceptions::PyException::new_err(format!("{}", e)))
    }
}